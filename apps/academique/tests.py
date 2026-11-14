import datetime

from django.test import TestCase

from apps.comptes.models import Utilisateur

from .models import Affectation, AnneeScolaire, Classe, Matiere


class GestionPagesTests(TestCase):
    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            "admin", "admin@example.com", "MotDePasse-Solide-2026",
            role=Utilisateur.Role.ADMINISTRATEUR,
        )
        self.prof = Utilisateur.objects.create_user(
            "prof", "prof@example.com", "MotDePasse-Solide-2026",
            role=Utilisateur.Role.PROFESSEUR,
        )
        self.annee = AnneeScolaire.objects.create(
            libelle="2026-2027",
            date_debut=datetime.date(2026, 9, 1),
            date_fin=datetime.date(2027, 8, 31),
        )
        self.classe = Classe.objects.create(nom="6e A", annee=self.annee)
        self.matiere = Matiere.objects.create(nom="Mathématiques")

    def test_gestion_academique_reservee_a_l_administrateur(self):
        self.client.force_login(self.prof)
        self.assertEqual(self.client.get("/gestion/affectations/").status_code, 403)
        self.assertEqual(self.client.get("/gestion/referentiels/").status_code, 403)

    def test_administrateur_peut_creer_et_modifier_une_affectation(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/gestion/affectations/",
            {
                "professeur": self.prof.pk,
                "classe": self.classe.pk,
                "matiere": self.matiere.pk,
            },
        )
        self.assertRedirects(response, "/gestion/affectations/")
        affectation = Affectation.objects.get()
        self.assertEqual(affectation.professeur, self.prof)
        self.assertContains(
            self.client.get(f"/gestion/affectations/?modifier={affectation.pk}"),
            "Modifier l’affectation",
        )

    def test_administrateur_peut_ajouter_un_referentiel(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/gestion/referentiels/",
            {
                "action": "matiere",
                "object_id": "",
                "nom": "Français",
            },
        )
        self.assertRedirects(response, "/gestion/referentiels/")
        self.assertTrue(Matiere.objects.filter(nom="Français").exists())
