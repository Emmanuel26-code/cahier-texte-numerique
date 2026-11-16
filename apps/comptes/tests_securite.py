"""Sécurité des comptes : limite de tentatives, confirmation de l'e-mail, validation des professeurs."""
import re

from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.comptes.models import Utilisateur
from apps.comptes.securite import SEL_CONFIRMATION, jeton_confirmation

MDP = "MotDePasse-Solide-2026"
Role = Utilisateur.Role


class LimiteTentativesConnexionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.compte = Utilisateur.objects.create_user(email="awa@ecole.ci", password=MDP)

    def connecter(self, mot_de_passe, email="awa@ecole.ci", ip="10.0.0.1"):
        return self.client.post("/comptes/connexion/", {"username": email, "password": mot_de_passe},
                                REMOTE_ADDR=ip)

    def test_bloque_apres_5_echecs_meme_avec_le_bon_mot_de_passe(self):
        for _ in range(5):
            self.connecter("mauvais")
        reponse = self.connecter(MDP)
        self.assertContains(reponse, "Réessayez dans 15 minutes.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_blocage_par_e_mail_meme_en_changeant_d_adresse_ip(self):
        for i in range(5):
            self.connecter("mauvais", ip=f"10.0.0.{i + 10}")
        self.assertContains(self.connecter(MDP, ip="10.9.9.9"), "Réessayez dans 15 minutes.")

    def test_blocage_par_ip_meme_en_changeant_d_e_mail(self):
        for i in range(5):
            self.connecter("mauvais", email=f"inconnu{i}@ecole.ci")
        self.assertContains(self.connecter(MDP), "Réessayez dans 15 minutes.")

    def test_moins_de_5_echecs_puis_succes(self):
        for _ in range(4):
            self.connecter("mauvais")
        self.assertRedirects(self.connecter(MDP), "/tableau-de-bord/", fetch_redirect_response=False)

    def test_le_blocage_vaut_pour_toute_authentification(self):
        """Le contrôle est dans le backend : il protège aussi l'admin Django si on la réactive."""
        from django.contrib.auth import authenticate
        from django.test import RequestFactory

        requete = RequestFactory().post("/", REMOTE_ADDR="10.0.0.2")
        for _ in range(5):
            authenticate(requete, username="awa@ecole.ci", password="mauvais")
        self.assertIsNone(authenticate(requete, username="awa@ecole.ci", password=MDP))

    def test_admin_django_desactivee_par_defaut(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_CONFIGURE=True)
class ConfirmationEmailTests(TestCase):
    donnees = {
        "first_name": "Koffi", "last_name": "Yao", "email": "koffi@ecole.ci", "role": "eleve", "classe": "6e A",
        "password1": MDP, "password2": MDP,
    }

    def setUp(self):
        cache.clear()

    def lien(self):
        return re.search(r"https?://testserver(/comptes/confirmer/[^\s]+/)", mail.outbox[-1].body).group(1)

    def test_parcours_complet(self):
        reponse = self.client.post("/comptes/inscription/", self.donnees)
        self.assertRedirects(reponse, "/comptes/inscription/envoyee/")
        self.assertNotIn("_auth_user_id", self.client.session)  # pas de connexion avant confirmation
        compte = Utilisateur.objects.get(email="koffi@ecole.ci")
        self.assertFalse(compte.email_verifie)
        self.assertEqual(mail.outbox[0].to, ["koffi@ecole.ci"])
        self.assertIn("Confirmez votre adresse", mail.outbox[0].subject)

        refus = self.client.post("/comptes/connexion/", {"username": "koffi@ecole.ci", "password": MDP})
        self.assertContains(refus, "Confirmez d’abord votre adresse e-mail")
        self.assertContains(refus, "Renvoyer le lien de confirmation")

        self.assertContains(self.client.get(self.lien()), "Adresse confirmée")
        compte.refresh_from_db()
        self.assertTrue(compte.email_verifie)
        self.assertRedirects(self.client.post("/comptes/connexion/", {"username": "koffi@ecole.ci", "password": MDP}),
                             "/tableau-de-bord/", fetch_redirect_response=False)

    def test_mauvais_mot_de_passe_ne_revele_pas_l_etat_du_compte(self):
        self.client.post("/comptes/inscription/", self.donnees)
        reponse = self.client.post("/comptes/connexion/", {"username": "koffi@ecole.ci", "password": "faux"})
        self.assertContains(reponse, "Adresse e-mail ou mot de passe incorrect")
        self.assertNotContains(reponse, "Confirmez d’abord")

    def test_lien_invalide_ou_expire(self):
        self.assertContains(self.client.get("/comptes/confirmer/nimporte-quoi/"), "Lien invalide")
        compte = Utilisateur.objects.create_user(email="lent@ecole.ci", password=MDP, email_verifie=False)
        jeton = jeton_confirmation(compte)
        with self.settings(SIGNING_BACKEND="django.core.signing.TimestampSigner"):
            from unittest.mock import patch
            with patch("apps.comptes.securite.VALIDITE_CONFIRMATION", -1):
                self.assertContains(self.client.get(f"/comptes/confirmer/{jeton}/"), "Lien expiré")
        compte.refresh_from_db()
        self.assertFalse(compte.email_verifie)

    def test_jeton_falsifie_refuse(self):
        compte = Utilisateur.objects.create_user(email="cible@ecole.ci", password=MDP, email_verifie=False)
        faux = signing.dumps({"id": compte.pk, "email": compte.email}, salt=SEL_CONFIRMATION, key="autre-cle")
        self.assertContains(self.client.get(f"/comptes/confirmer/{faux}/"), "Lien invalide")
        compte.refresh_from_db()
        self.assertFalse(compte.email_verifie)

    def test_renvoyer_le_lien(self):
        self.client.post("/comptes/inscription/", self.donnees)
        self.client.post("/comptes/confirmer-renvoyer/", {"email": "KOFFI@ecole.ci"})
        self.assertEqual(len(mail.outbox), 2)
        reponse = self.client.post("/comptes/confirmer-renvoyer/", {"email": "inconnu@ecole.ci"}, follow=True)
        self.assertContains(reponse, "Si cette adresse attend une confirmation")  # même réponse
        self.assertEqual(len(mail.outbox), 2)

    def test_trop_d_inscriptions_depuis_la_meme_connexion(self):
        for i in range(5):
            self.client.post("/comptes/inscription/", {**self.donnees, "email": f"eleve{i}@ecole.ci"})
        reponse = self.client.post("/comptes/inscription/", {**self.donnees, "email": "eleve9@ecole.ci"})
        self.assertContains(reponse, "Trop d’inscriptions depuis cette connexion")
        self.assertFalse(Utilisateur.objects.filter(email="eleve9@ecole.ci").exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_CONFIGURE=True)
class ValidationProfesseursTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = Utilisateur.objects.create_user(email="direction@ecole.ci", password=MDP, role=Role.ADMINISTRATEUR)
        self.client.post("/comptes/inscription/", {
            "first_name": "Yao", "last_name": "Kouassi", "email": "yao@ecole.ci", "role": "professeur",
            "password1": MDP, "password2": MDP,
        })
        self.prof = Utilisateur.objects.get(email="yao@ecole.ci")
        lien = re.search(r"https?://testserver(/comptes/confirmer/[^\s]+/)", mail.outbox[-1].body).group(1)
        self.page_confirmation = self.client.get(lien)

    def connecter_prof(self):
        return self.client.post("/comptes/connexion/", {"username": "yao@ecole.ci", "password": MDP})

    def test_professeur_en_attente_apres_confirmation(self):
        self.assertContains(self.page_confirmation, "attend maintenant la validation")
        self.prof.refresh_from_db()
        self.assertTrue(self.prof.email_verifie)
        self.assertTrue(self.prof.en_attente_validation)
        self.assertIn("direction@ecole.ci", mail.outbox[-1].to)  # l'administration est prévenue
        self.assertContains(self.connecter_prof(), "attend la validation de l’administration")

    def test_l_administration_valide(self):
        self.client.force_login(self.admin)
        page = self.client.get(f"/comptes/utilisateurs/?modifier={self.prof.pk}")
        self.assertContains(page, "Valider le compte")
        self.client.post(f"/comptes/utilisateurs/{self.prof.pk}/valider/")
        self.prof.refresh_from_db()
        self.assertFalse(self.prof.en_attente_validation)
        self.assertEqual(mail.outbox[-1].to, ["yao@ecole.ci"])
        self.assertIn("validé", mail.outbox[-1].subject)
        self.client.logout()
        self.assertRedirects(self.connecter_prof(), "/tableau-de-bord/", fetch_redirect_response=False)

    def test_l_administration_refuse(self):
        self.client.force_login(self.admin)
        self.client.post(f"/comptes/utilisateurs/{self.prof.pk}/refuser/")
        self.assertFalse(Utilisateur.objects.filter(email="yao@ecole.ci").exists())

    def test_seule_l_administration_peut_valider(self):
        eleve = Utilisateur.objects.create_user(email="eleve@ecole.ci", password=MDP)
        self.client.force_login(eleve)
        self.assertEqual(self.client.post(f"/comptes/utilisateurs/{self.prof.pk}/valider/").status_code, 403)
        self.prof.refresh_from_db()
        self.assertTrue(self.prof.en_attente_validation)

    def test_tableau_de_bord_admin_signale_la_demande(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get("/tableau-de-bord/administrateur/"), "1 compte professeur à valider")

    def test_comptes_crees_par_l_administration_utilisables_tout_de_suite(self):
        self.client.force_login(self.admin)
        self.client.post("/comptes/utilisateurs/", {
            "email": "nouveau.prof@ecole.ci", "first_name": "Ama", "last_name": "Diallo",
            "role": "professeur", "is_active": "on", "mot_de_passe": "S3cure!User2026",
        })
        compte = Utilisateur.objects.get(email="nouveau.prof@ecole.ci")
        self.assertTrue(compte.email_verifie)
        self.assertFalse(compte.en_attente_validation)


class ClasseChoisieALInscriptionTests(TestCase):
    """L'élève indique sa classe ; il y est inscrit tout de suite, ou dès qu'elle est créée."""

    def setUp(self):
        import datetime
        from apps.academique.models import AnneeScolaire
        cache.clear()
        aujourd_hui = datetime.date.today()
        self.annee = AnneeScolaire.objects.create(
            libelle="en-cours", date_debut=aujourd_hui - datetime.timedelta(days=30),
            date_fin=aujourd_hui + datetime.timedelta(days=200))

    def inscrire(self, classe, email="eleve@ecole.ci", role="eleve"):
        return self.client.post("/comptes/inscription/", {
            "first_name": "Awa", "last_name": "Kone", "email": email, "role": role, "classe": classe,
            "password1": MDP, "password2": MDP,
        })

    def test_classe_existante_inscription_immediate(self):
        from apps.academique.models import Classe
        classe = Classe.objects.create(nom="6e A", annee=self.annee)
        self.inscrire("  6E   a ")  # casse et espaces ignorés
        eleve = Utilisateur.objects.get(email="eleve@ecole.ci")
        self.assertEqual(list(eleve.classes_suivies.all()), [classe])
        self.assertEqual(eleve.classe_demandee, "")

    def test_classe_pas_encore_creee_inscription_automatique_plus_tard(self):
        from apps.academique.models import Classe
        self.inscrire("Tle D")
        eleve = Utilisateur.objects.get(email="eleve@ecole.ci")
        self.assertEqual(eleve.classe_demandee, "Tle D")
        self.assertFalse(eleve.classes_suivies.exists())
        classe = Classe.objects.create(nom="TLE D", annee=self.annee)  # l'administration crée la classe
        eleve.refresh_from_db()
        self.assertEqual(list(eleve.classes_suivies.all()), [classe])
        self.assertEqual(eleve.classe_demandee, "")

    def test_classe_obligatoire_pour_un_eleve(self):
        reponse = self.inscrire("")
        self.assertContains(reponse, "Indiquez votre classe.")
        self.assertFalse(Utilisateur.objects.filter(email="eleve@ecole.ci").exists())

    def test_pas_de_classe_pour_un_professeur(self):
        self.inscrire("", email="prof@ecole.ci", role="professeur")
        prof = Utilisateur.objects.get(email="prof@ecole.ci")
        self.assertEqual(prof.classe_demandee, "")
        self.assertFalse(prof.classes_suivies.exists())

    def test_suggestions_des_classes_existantes(self):
        from apps.academique.models import Classe
        Classe.objects.create(nom="5e B", annee=self.annee)
        self.assertContains(self.client.get("/comptes/inscription/"), '<option value="5e B">')

    def test_l_administration_voit_la_demande(self):
        self.inscrire("3e C")
        admin = Utilisateur.objects.create_user(email="dir@ecole.ci", password=MDP, role=Role.ADMINISTRATEUR)
        self.client.force_login(admin)
        self.assertContains(self.client.get("/comptes/utilisateurs/"), "Demande : 3e C")


class EnTetesEtPagesTests(TestCase):
    def test_politique_de_securite_du_contenu(self):
        reponse = self.client.get("/comptes/connexion/")
        csp = reponse["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("camera=()", reponse["Permissions-Policy"])

    def test_aucun_script_dans_les_pages(self):
        import pathlib
        racines = [pathlib.Path("templates"), pathlib.Path("apps")]
        fautifs = [str(f) for r in racines for f in r.rglob("*.html")
                   if "/emails/" not in f.as_posix()
                   and re.search(r"<script>|on(click|submit|change|load)=", f.read_text(encoding="utf-8"))]
        self.assertEqual(fautifs, [])  # sinon la CSP les bloquerait

    def test_jeton_csrf_dans_une_balise_meta(self):
        self.assertContains(self.client.get("/comptes/connexion/"), '<meta name="csrf-token"')

    def test_page_404_personnalisee(self):
        reponse = self.client.get("/page-qui-n-existe-pas/")
        self.assertContains(reponse, "Page introuvable", status_code=404)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_CONFIGURE=True)
class InscriptionAdresseExistanteTests(TestCase):
    def test_le_titulaire_est_prevenu(self):
        cache.clear()
        Utilisateur.objects.create_user(email="awa@ecole.ci", password=MDP)
        self.client.post("/comptes/inscription/", {
            "first_name": "X", "last_name": "Y", "email": "awa@ecole.ci", "role": "eleve", "classe": "6e A",
            "password1": MDP, "password2": MDP,
        })
        self.assertEqual(mail.outbox[-1].to, ["awa@ecole.ci"])
        self.assertIn("Tentative d’inscription", mail.outbox[-1].subject)
        self.assertTrue(Utilisateur.objects.get(email="awa@ecole.ci").check_password(MDP))  # compte inchangé
