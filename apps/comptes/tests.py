import re
import datetime

from apps.academique.models import AnneeScolaire, Classe
from django.test import TestCase

from .models import Utilisateur


class UtilisateurTests(TestCase):
    def test_role_par_defaut_eleve(self):
        u = Utilisateur.objects.create_user("eleve1", "e1@example.com", "motdepasse123")
        self.assertEqual(u.role, Utilisateur.Role.ELEVE)
        self.assertTrue(u.check_password("motdepasse123"))  # mot de passe haché


class InscriptionConnexionTests(TestCase):
    donnees = {
        "first_name": "Awa",
        "last_name": "Kone",
        "email": "awa@example.com",
        "role": "professeur",
        "password1": "MotDePasse-Solide-2026",
        "password2": "MotDePasse-Solide-2026",
    }

    def test_inscription_cree_un_compte_au_mot_de_passe_hache(self):
        reponse = self.client.post("/comptes/inscription/", self.donnees)
        self.assertRedirects(reponse, "/tableau-de-bord/", fetch_redirect_response=False)
        u = Utilisateur.objects.get(email="awa@example.com")
        self.assertEqual(u.username, "awa")  # identifiant interne généré à partir de l'e-mail
        self.assertNotEqual(u.password, "MotDePasse-Solide-2026")  
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))

    def test_on_ne_peut_pas_s_inscrire_administrateur(self):
        self.client.post("/comptes/inscription/", {**self.donnees, "role": "administrateur"})
        self.assertFalse(Utilisateur.objects.filter(email="awa@example.com").exists())

    def test_connexion_et_deconnexion(self):
        Utilisateur.objects.create_user("eleve2", "e2@example.com", "MotDePasse-Solide-2026")
        reponse = self.client.post(
            "/comptes/connexion/", {"username": "E2@Example.com", "password": "MotDePasse-Solide-2026"}  # e-mail, casse ignorée
        )
        self.assertRedirects(reponse, "/tableau-de-bord/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session) 
        self.client.post("/comptes/deconnexion/")
        self.assertNotIn("_auth_user_id", self.client.session)  

    def test_le_formulaire_ne_demande_pas_de_nom_d_utilisateur(self):
        reponse = self.client.get("/comptes/inscription/")
        self.assertNotIn("username", reponse.context["form"].fields)

    def test_deux_e_mails_identiques_a_la_casse_pres_refuses(self):
        self.client.post("/comptes/inscription/", self.donnees)
        self.client.logout()
        reponse = self.client.post("/comptes/inscription/", {**self.donnees, "email": "AWA@example.com"})
        self.assertContains(reponse, "Un compte existe déjà avec cette adresse e-mail.")
        self.assertEqual(Utilisateur.objects.count(), 1)

    def test_identifiants_internes_uniques(self):
        a = Utilisateur.objects.create_user(email="awa@ecole.ci", password="x" * 12)
        b = Utilisateur.objects.create_user(email="awa@autre.ci", password="x" * 12)
        self.assertEqual((a.username, b.username), ("awa", "awa2"))

    def test_mauvais_mot_de_passe_refuse(self):
        Utilisateur.objects.create_user("eleve3", "e3@example.com", "MotDePasse-Solide-2026")
        reponse = self.client.post("/comptes/connexion/", {"username": "e3@example.com", "password": "faux"})
        self.assertEqual(reponse.status_code, 200)  
        self.assertNotIn("_auth_user_id", self.client.session)

class RolesTests(TestCase):
    def setUp(self):
        mdp = "MotDePasse-Solide-2026"
        self.prof = Utilisateur.objects.create_user("prof", "prof@example.com", mdp, role="professeur")
        self.eleve = Utilisateur.objects.create_user("eleve", "eleve@example.com", mdp, role="eleve")
        self.admin = Utilisateur.objects.create_user("admin1", "admin@example.com", mdp, role="administrateur")

    def test_proprietes_de_role(self):
        self.assertTrue(self.prof.est_professeur)
        self.assertTrue(self.eleve.est_eleve)
        self.assertTrue(self.admin.est_administrateur)
        self.assertFalse(self.eleve.est_professeur)

    def test_superuser_devient_administrateur(self):
        su = Utilisateur.objects.create_superuser("root", "root@example.com", "MotDePasse-Solide-2026")
        self.assertEqual(su.role, Utilisateur.Role.ADMINISTRATEUR)

    def acces_importer(self, utilisateur):
        if utilisateur:
            self.client.force_login(utilisateur)
        return self.client.get("/documents/importer/").status_code

    def test_professeur_peut_importer(self):
        self.assertEqual(self.acces_importer(self.prof), 200)

    def test_eleve_ne_peut_pas_importer(self):
        self.assertEqual(self.acces_importer(self.eleve), 403)

    def test_administrateur_peut_importer_un_document_de_gestion(self):
        self.assertEqual(self.acces_importer(self.admin), 200)

    def test_visiteur_redirige_vers_la_connexion(self):
        reponse = self.client.get("/documents/importer/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/comptes/connexion/", reponse["Location"])

    def test_liste_des_documents_selon_le_role(self):
        self.client.force_login(self.eleve)
        self.assertEqual(self.client.get("/documents/").status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/documents/").status_code, 200)

    def test_page_403_personnalisee(self):
        self.client.force_login(self.eleve)
        reponse = self.client.get("/documents/importer/")
        self.assertContains(reponse, "Accès interdit", status_code=403)

    def test_menu_selon_le_role(self):
        self.client.force_login(self.prof)
        self.assertContains(self.client.get("/", follow=True), "Importer un cours")
        self.client.force_login(self.eleve)
        self.assertNotContains(self.client.get("/", follow=True), "Importer un cours")


class GestionUtilisateursTests(TestCase):
    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            "admin-ui", "admin-ui@example.com", "MotDePasse-Solide-2026",
            role=Utilisateur.Role.ADMINISTRATEUR,
        )
        self.annee = AnneeScolaire.objects.create(
            libelle="2026-2027",
            date_debut=datetime.date(2026, 9, 1),
            date_fin=datetime.date(2027, 8, 31),
        )
        self.classe = Classe.objects.create(nom="6e A", annee=self.annee)
        self.client.force_login(self.admin)

    def test_page_utilisateurs_est_disponible_a_l_administrateur(self):
        response = self.client.get("/comptes/utilisateurs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Utilisateurs de l’établissement")

    def test_creation_eleve_et_inscription_a_une_classe(self):
        response = self.client.post(
            "/comptes/utilisateurs/",
            {
                "first_name": "Aminata",
                "last_name": "Traore",
                "email": "aminata@example.com",
                "role": Utilisateur.Role.ELEVE,
                "is_active": "on",
                "mot_de_passe": "S3cure!User2026",
                "classes": [self.classe.pk],
            },
        )
        self.assertRedirects(response, "/comptes/utilisateurs/")
        eleve = Utilisateur.objects.get(email="aminata@example.com")
        self.assertTrue(eleve.check_password("S3cure!User2026"))
        self.assertEqual(list(eleve.classes_suivies.all()), [self.classe])

class GestionUtilisateursEmailTests(TestCase):
    """La page Utilisateurs ne demande plus de nom d'utilisateur et protège l'unicité de l'e-mail."""

    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            email="direction@ecole.ci", password="MotDePasse-Solide-2026", role=Utilisateur.Role.ADMINISTRATEUR)
        self.client.force_login(self.admin)

    def test_pas_de_champ_nom_d_utilisateur(self):
        reponse = self.client.get("/comptes/utilisateurs/?nouveau=1")
        self.assertNotIn("username", reponse.context["form"].fields)
        self.assertContains(reponse, "Adresse e-mail (identifiant de connexion)")

    def test_e_mail_deja_pris_refuse_meme_avec_majuscules(self):
        Utilisateur.objects.create_user(email="awa@ecole.ci", password="x" * 12)
        reponse = self.client.post("/comptes/utilisateurs/", {
            "email": "AWA@ecole.ci", "first_name": "Awa", "last_name": "Bis", "role": "eleve",
            "is_active": "on", "mot_de_passe": "S3cure!User2026",
        })
        self.assertContains(reponse, "Un compte existe déjà avec cette adresse e-mail.")
        self.assertEqual(Utilisateur.objects.filter(email__iexact="awa@ecole.ci").count(), 1)

    def test_modifier_un_compte_sans_changer_son_e_mail(self):
        eleve = Utilisateur.objects.create_user(email="koffi@ecole.ci", password="x" * 12, first_name="Koffi")
        reponse = self.client.post("/comptes/utilisateurs/", {
            "user_id": eleve.pk, "email": "koffi@ecole.ci", "first_name": "Koffi", "last_name": "Yao",
            "role": "eleve", "is_active": "on",
        })
        self.assertRedirects(reponse, "/comptes/utilisateurs/")
        eleve.refresh_from_db()
        self.assertEqual(eleve.last_name, "Yao")
        self.assertTrue(eleve.check_password("x" * 12))  # mot de passe conservé


from django.core import mail  # noqa: E402
from django.core.cache import cache  # noqa: E402
from django.test import override_settings  # noqa: E402


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_CONFIGURE=True)
class MotDePasseOublieTests(TestCase):
    def setUp(self):
        cache.clear()
        self.compte = Utilisateur.objects.create_user(
            email="awa@ecole.ci", password="Ancien-MotDePasse-2026", first_name="Awa")

    def demander(self, email="awa@ecole.ci"):
        return self.client.post("/comptes/mot-de-passe-oublie/", {"email": email})

    def test_lien_envoye_puis_nouveau_mot_de_passe(self):
        reponse = self.demander("AWA@ecole.ci")  # la casse ne compte pas
        self.assertRedirects(reponse, "/comptes/mot-de-passe-oublie/envoye/")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["awa@ecole.ci"])
        self.assertIn("Réinitialisation", message.subject)
        self.assertIn("Bonjour Awa", message.body)
        lien = re.search(r"https?://[^\s]+/comptes/reinitialiser/[^\s]+/", message.body).group(0)
        chemin = lien.split("testserver", 1)[1]
        page = self.client.get(chemin, follow=True)  # Django redirige vers une URL sans le jeton
        self.assertContains(page, "Nouveau mot de passe")
        reponse = self.client.post(page.redirect_chain[-1][0], {
            "new_password1": "Nouveau-MotDePasse-2026", "new_password2": "Nouveau-MotDePasse-2026"})
        self.assertRedirects(reponse, "/comptes/reinitialiser/termine/")
        self.compte.refresh_from_db()
        self.assertTrue(self.compte.check_password("Nouveau-MotDePasse-2026"))
        # le lien ne sert qu'une fois
        self.assertContains(self.client.get(chemin, follow=True), "Lien expiré")

    def test_adresse_inconnue_meme_reponse_sans_e_mail(self):
        reponse = self.demander("inconnu@ecole.ci")
        self.assertRedirects(reponse, "/comptes/mot-de-passe-oublie/envoye/")
        self.assertEqual(len(mail.outbox), 0)  # on ne révèle pas si le compte existe

    def test_trop_de_demandes_bloquees(self):
        for _ in range(5):
            self.demander()
        reponse = self.demander()
        self.assertContains(reponse, "Trop de demandes en peu de temps")
        self.assertEqual(len(mail.outbox), 5)

    @override_settings(EMAIL_CONFIGURE=False, DEBUG=False)
    def test_message_si_envoi_non_configure(self):
        self.assertContains(self.client.get("/comptes/mot-de-passe-oublie/"), "L’envoi d’e-mails n’est pas encore activé")

    def test_lien_sur_la_page_de_connexion(self):
        self.assertContains(self.client.get("/comptes/connexion/"), "/comptes/mot-de-passe-oublie/")


class SessionEtChangementDeCompteTests(TestCase):
    def setUp(self):
        Utilisateur.objects.create_user(email="koffi@ecole.ci", password="MotDePasse-Solide-2026")

    def connecter(self, **extra):
        return self.client.post("/comptes/connexion/", {"username": "koffi@ecole.ci", "password": "MotDePasse-Solide-2026", **extra})

    def test_rester_connecte_garde_la_session_60_jours(self):
        self.connecter(rester_connecte="on")
        self.assertEqual(self.client.session.get_expiry_age(), 60 * 24 * 3600)
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_sans_rester_connecte_session_jusqu_a_fermeture(self):
        self.connecter()
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_case_cochee_par_defaut(self):
        html = self.client.get("/comptes/connexion/").content.decode()
        self.assertRegex(html, r'<input[^>]*name="rester_connecte"[^>]*checked')

    def test_changer_de_compte_deconnecte_et_ouvre_la_connexion(self):
        self.connecter(rester_connecte="on")
        reponse = self.client.post("/comptes/deconnexion/", {"next": "/comptes/connexion/"})
        self.assertRedirects(reponse, "/comptes/connexion/")
        self.assertNotIn("_auth_user_id", self.client.session)
