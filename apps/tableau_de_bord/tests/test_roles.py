"""Tâche 51 : tests fonctionnels par rôle.

Règles vérifiées (d'après les consignes de l'équipe) :
  1. trois rôles existent : professeur, élève, administrateur ;
  2. l'inscription publique n'autorise que professeur ou élève ;
  3. un compte administrateur se crée avec `createsuperuser` et reçoit ce rôle automatiquement ;
  4. connecté avec le mauvais rôle -> page « Accès interdit » (403) ;
     visiteur non connecté -> redirection vers la connexion ;
  5. les mots de passe sont hachés (PBKDF2).

À ADAPTER dans votre dépôt (3 endroits, en haut du fichier) : l'import du modèle,
le nom de l'URL d'inscription et les noms des URLs des tableaux de bord.
"""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.comptes.models import Utilisateur

Role = Utilisateur.Role

URL_CONNEXION = "comptes:connexion"
URL_INSCRIPTION = "comptes:inscription"
TABLEAU_DE_BORD = {  # rôle -> nom de l'URL de son tableau de bord
    Role.ELEVE: "tableau_de_bord:eleve",
    Role.PROFESSEUR: "tableau_de_bord:professeur",
    Role.ADMINISTRATEUR: "tableau_de_bord:administrateur",
}
MOT_DE_PASSE = "Motdepasse-Solide-2026"


def creer(role, nom=None):
    return Utilisateur.objects.create_user(username=nom or f"{role}_test", password=MOT_DE_PASSE, role=role)


class TroisRolesTests(TestCase):
    def test_les_trois_roles_existent(self):
        self.assertEqual(
            {r.value for r in Role},
            {"professeur", "eleve", "administrateur"},
        )


class InscriptionPubliqueTests(TestCase):
    def poster(self, role, nom="nouveau"):
        return self.client.post(reverse(URL_INSCRIPTION), {
            "username": nom, "first_name": "Awa", "last_name": "Test", "email": f"{nom}@exemple.ci",
            "role": role, "password1": MOT_DE_PASSE, "password2": MOT_DE_PASSE,
        })

    def test_inscription_professeur_acceptee(self):
        reponse = self.poster(Role.PROFESSEUR, "prof1")
        self.assertRedirects(reponse, reverse("tableau_de_bord:accueil"), fetch_redirect_response=False)
        self.assertEqual(Utilisateur.objects.get(username="prof1").role, Role.PROFESSEUR)

    def test_inscription_eleve_acceptee(self):
        self.poster(Role.ELEVE, "eleve1")
        self.assertEqual(Utilisateur.objects.get(username="eleve1").role, Role.ELEVE)

    def test_inscription_administrateur_refusee(self):
        reponse = self.poster(Role.ADMINISTRATEUR, "pirate")
        self.assertEqual(reponse.status_code, 200)  # le formulaire est réaffiché avec une erreur
        self.assertFalse(Utilisateur.objects.filter(username="pirate").exists())

    def test_inscription_role_inconnu_refusee(self):
        self.poster("directeur", "intrus")
        self.assertFalse(Utilisateur.objects.filter(username="intrus").exists())

    def test_le_formulaire_ne_propose_que_professeur_et_eleve(self):
        reponse = self.client.get(reverse(URL_INSCRIPTION))
        propositions = {valeur for valeur, _ in reponse.context["form"].fields["role"].choices}
        self.assertEqual(propositions, {Role.PROFESSEUR, Role.ELEVE})

    def test_mot_de_passe_hache_en_pbkdf2(self):
        self.poster(Role.ELEVE, "hache")
        enregistre = Utilisateur.objects.get(username="hache").password
        self.assertTrue(enregistre.startswith("pbkdf2_sha256$"))
        self.assertNotIn(MOT_DE_PASSE, enregistre)


class CreationAdministrateurTests(TestCase):
    def test_createsuperuser_donne_le_role_administrateur(self):
        call_command("createsuperuser", interactive=False, username="direction",
                     email="direction@exemple.ci", verbosity=0)
        admin = Utilisateur.objects.get(username="direction")
        self.assertEqual(admin.role, Role.ADMINISTRATEUR)
        self.assertTrue(admin.is_superuser)

    def test_un_utilisateur_ordinaire_n_est_pas_superuser(self):
        self.assertFalse(creer(Role.PROFESSEUR).is_superuser)


class AccesParRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.comptes = {role: creer(role) for role in Role}

    def test_chaque_role_accede_a_son_tableau_de_bord(self):
        for role, nom_url in TABLEAU_DE_BORD.items():
            with self.subTest(role=role):
                self.client.force_login(self.comptes[role])
                self.assertEqual(self.client.get(reverse(nom_url)).status_code, 200)

    def test_mauvais_role_voit_acces_interdit_403(self):
        for role, compte in self.comptes.items():
            for role_cible, nom_url in TABLEAU_DE_BORD.items():
                if role_cible == role:
                    continue
                with self.subTest(connecte_en=role, page_de=role_cible):
                    self.client.force_login(compte)
                    reponse = self.client.get(reverse(nom_url))
                    self.assertContains(reponse, "Accès interdit", status_code=403)

    def test_visiteur_non_connecte_renvoye_a_la_connexion(self):
        for role_cible, nom_url in TABLEAU_DE_BORD.items():
            with self.subTest(page_de=role_cible):
                url = reverse(nom_url)
                reponse = self.client.get(url)
                self.assertRedirects(reponse, f"{reverse(URL_CONNEXION)}?next={url}", fetch_redirect_response=False)

    def test_accueil_oriente_vers_le_tableau_de_bord_du_role(self):
        for role, nom_url in TABLEAU_DE_BORD.items():
            with self.subTest(role=role):
                self.client.force_login(self.comptes[role])
                reponse = self.client.get(reverse("tableau_de_bord:accueil"))
                self.assertRedirects(reponse, reverse(nom_url), fetch_redirect_response=False)

    def test_connexion_puis_redirection_selon_le_role(self):
        reponse = self.client.post(reverse(URL_CONNEXION), {
            "username": self.comptes[Role.ELEVE].username, "password": MOT_DE_PASSE})
        self.assertRedirects(reponse, reverse("tableau_de_bord:accueil"), fetch_redirect_response=False)
