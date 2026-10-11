from django.test import TestCase

from .models import Utilisateur


class UtilisateurTests(TestCase):
    def test_role_par_defaut_eleve(self):
        u = Utilisateur.objects.create_user("eleve1", "e1@example.com", "motdepasse123")
        self.assertEqual(u.role, Utilisateur.Role.ELEVE)
        self.assertTrue(u.check_password("motdepasse123"))  # mot de passe haché


class InscriptionConnexionTests(TestCase):
    donnees = {
        "username": "prof1",
        "first_name": "Awa",
        "last_name": "Kone",
        "email": "awa@example.com",
        "role": "professeur",
        "password1": "MotDePasse-Solide-2026",
        "password2": "MotDePasse-Solide-2026",
    }

    def test_inscription_cree_un_compte_au_mot_de_passe_hache(self):
        reponse = self.client.post("/comptes/inscription/", self.donnees)
        self.assertRedirects(reponse, "/")
        u = Utilisateur.objects.get(username="prof1")
        self.assertNotEqual(u.password, "MotDePasse-Solide-2026")  # jamais en clair
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))

    def test_on_ne_peut_pas_s_inscrire_administrateur(self):
        self.client.post("/comptes/inscription/", {**self.donnees, "role": "administrateur"})
        self.assertFalse(Utilisateur.objects.filter(username="prof1").exists())

    def test_connexion_et_deconnexion(self):
        Utilisateur.objects.create_user("eleve2", "e2@example.com", "MotDePasse-Solide-2026")
        reponse = self.client.post(
            "/comptes/connexion/", {"username": "eleve2", "password": "MotDePasse-Solide-2026"}
        )
        self.assertRedirects(reponse, "/")
        self.assertIn("_auth_user_id", self.client.session)  # connecté
        self.client.post("/comptes/deconnexion/")
        self.assertNotIn("_auth_user_id", self.client.session)  # déconnecté

    def test_mauvais_mot_de_passe_refuse(self):
        Utilisateur.objects.create_user("eleve3", "e3@example.com", "MotDePasse-Solide-2026")
        reponse = self.client.post("/comptes/connexion/", {"username": "eleve3", "password": "faux"})
        self.assertEqual(reponse.status_code, 200)  # reste sur la page, avec erreur
        self.assertNotIn("_auth_user_id", self.client.session)