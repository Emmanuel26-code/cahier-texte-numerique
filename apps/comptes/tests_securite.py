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
        self.assertContains(reponse, "Trop de tentatives de connexion")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_blocage_par_e_mail_meme_en_changeant_d_adresse_ip(self):
        for i in range(5):
            self.connecter("mauvais", ip=f"10.0.0.{i + 10}")
        self.assertContains(self.connecter(MDP, ip="10.9.9.9"), "Trop de tentatives de connexion")

    def test_blocage_par_ip_meme_en_changeant_d_e_mail(self):
        for i in range(5):
            self.connecter("mauvais", email=f"inconnu{i}@ecole.ci")
        self.assertContains(self.connecter(MDP), "Trop de tentatives de connexion")

    def test_moins_de_5_echecs_puis_succes(self):
        for _ in range(4):
            self.connecter("mauvais")
        self.assertRedirects(self.connecter(MDP), "/tableau-de-bord/", fetch_redirect_response=False)

    def test_l_admin_django_est_aussi_protege(self):
        Utilisateur.objects.create_superuser(email="chef@ecole.ci", password=MDP)
        for _ in range(5):
            self.client.post("/admin/login/", {"username": "chef@ecole.ci", "password": "mauvais"}, REMOTE_ADDR="10.0.0.2")
        self.client.post("/admin/login/", {"username": "chef@ecole.ci", "password": MDP}, REMOTE_ADDR="10.0.0.2")
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_CONFIGURE=True)
class ConfirmationEmailTests(TestCase):
    donnees = {
        "first_name": "Koffi", "last_name": "Yao", "email": "koffi@ecole.ci", "role": "eleve",
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
