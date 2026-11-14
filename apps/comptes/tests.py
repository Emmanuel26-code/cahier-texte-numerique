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
        self.assertRedirects(reponse, "/tableau-de-bord/", fetch_redirect_response=False)
        u = Utilisateur.objects.get(username="prof1")
        self.assertNotEqual(u.password, "MotDePasse-Solide-2026")  
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))

    def test_on_ne_peut_pas_s_inscrire_administrateur(self):
        self.client.post("/comptes/inscription/", {**self.donnees, "role": "administrateur"})
        self.assertFalse(Utilisateur.objects.filter(username="prof1").exists())

    def test_connexion_et_deconnexion(self):
        Utilisateur.objects.create_user("eleve2", "e2@example.com", "MotDePasse-Solide-2026")
        reponse = self.client.post(
            "/comptes/connexion/", {"username": "eleve2", "password": "MotDePasse-Solide-2026"}
        )
        self.assertRedirects(reponse, "/tableau-de-bord/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session) 
        self.client.post("/comptes/deconnexion/")
        self.assertNotIn("_auth_user_id", self.client.session)  

    def test_mauvais_mot_de_passe_refuse(self):
        Utilisateur.objects.create_user("eleve3", "e3@example.com", "MotDePasse-Solide-2026")
        reponse = self.client.post("/comptes/connexion/", {"username": "eleve3", "password": "faux"})
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
        self.assertContains(self.client.get("/"), "Importer un cours")
        self.client.force_login(self.eleve)
        self.assertNotContains(self.client.get("/"), "Importer un cours")


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
                "username": "nouvel-eleve",
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
        eleve = Utilisateur.objects.get(username="nouvel-eleve")
        self.assertTrue(eleve.check_password("S3cure!User2026"))
        self.assertEqual(list(eleve.classes_suivies.all()), [self.classe])