"""Tâche 49 : contenu du tableau de bord élève (ce qu'il voit, ce qu'il ne doit PAS voir)."""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.academique.models import Affectation, Classe, Matiere
from apps.cahier.models import Seance
from apps.plans.models import Plan
from apps.comptes.models import Utilisateur

Role = Utilisateur.Role
URL = "tableau_de_bord:eleve"


class TableauDeBordEleveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.classe_a = Classe.objects.create(nom="6e A")
        cls.classe_b = Classe.objects.create(nom="5e B")
        maths = Matiere.objects.create(nom="Mathématiques")
        francais = Matiere.objects.create(nom="Français")
        prof = Utilisateur.objects.create_user("prof", password="x", role=Role.PROFESSEUR)
        cls.aff_a = Affectation.objects.create(professeur=prof, classe=cls.classe_a, matiere=maths)
        cls.aff_a_fr = Affectation.objects.create(professeur=prof, classe=cls.classe_a, matiere=francais)
        cls.aff_b = Affectation.objects.create(professeur=prof, classe=cls.classe_b, matiere=maths)
        cls.eleve = Utilisateur.objects.create_user(
            "eleve", password="x", role=Role.ELEVE, classe=cls.classe_a, first_name="Awa")

    def setUp(self):
        self.client.force_login(self.eleve)

    def test_affiche_travail_a_faire_et_seances_de_sa_classe(self):
        Seance.objects.create(affectation=self.aff_a, date=date(2026, 10, 12), titre="Addition de fractions",
                              travail_a_faire="Exercices 4 à 7, page 52", pour_le=date(2026, 10, 14))
        reponse = self.client.get(reverse(URL))
        self.assertContains(reponse, "Exercices 4 à 7, page 52")
        self.assertContains(reponse, "Addition de fractions")
        self.assertContains(reponse, "Bonjour, Awa")

    def test_ne_montre_pas_les_seances_des_autres_classes(self):
        Seance.objects.create(affectation=self.aff_b, date=date(2026, 10, 12), titre="Séance de la 5e B",
                              travail_a_faire="Devoir de la 5e B")
        reponse = self.client.get(reverse(URL))
        self.assertNotContains(reponse, "Séance de la 5e B")
        self.assertNotContains(reponse, "Devoir de la 5e B")

    def test_seance_sans_travail_n_apparait_pas_dans_travail_a_faire(self):
        Seance.objects.create(affectation=self.aff_a, date=date(2026, 10, 12), titre="Cours sans devoir")
        reponse = self.client.get(reverse(URL))
        self.assertEqual(reponse.context["travaux"], [])
        self.assertEqual(len(reponse.context["seances"]), 1)

    def test_seances_triees_de_la_plus_recente_a_la_plus_ancienne(self):
        for jour in (8, 12, 9):
            Seance.objects.create(affectation=self.aff_a, date=date(2026, 10, jour), titre=f"S{jour}")
        dates = [s.date.day for s in self.client.get(reverse(URL)).context["seances"]]
        self.assertEqual(dates, [12, 9, 8])

    def test_limite_a_cinq_elements(self):
        for jour in range(1, 9):
            Seance.objects.create(affectation=self.aff_a, date=date(2026, 10, jour), titre=f"S{jour}",
                                  travail_a_faire="à faire")
        contexte = self.client.get(reverse(URL)).context
        self.assertEqual(len(contexte["seances"]), 5)
        self.assertEqual(len(contexte["travaux"]), 5)

    def test_seuls_les_plans_valides_sont_visibles(self):
        Plan.objects.create(affectation=self.aff_a, titre="Plan validé", statut=Plan.Statut.VALIDE)
        Plan.objects.create(affectation=self.aff_a, titre="Plan brouillon", statut=Plan.Statut.BROUILLON)
        Plan.objects.create(affectation=self.aff_a, titre="Plan rejeté", statut=Plan.Statut.REJETE)
        Plan.objects.create(affectation=self.aff_b, titre="Plan validé autre classe", statut=Plan.Statut.VALIDE)
        reponse = self.client.get(reverse(URL))
        self.assertContains(reponse, "Plan validé")
        self.assertNotContains(reponse, "Plan brouillon")
        self.assertNotContains(reponse, "Plan rejeté")
        self.assertNotContains(reponse, "autre classe")

    def test_messages_quand_il_n_y_a_rien(self):
        reponse = self.client.get(reverse(URL))
        self.assertContains(reponse, "Aucun travail à faire pour le moment.")
        self.assertContains(reponse, "Aucune séance enregistrée.")
        self.assertContains(reponse, "Aucun plan de cours publié.")

    def test_eleve_sans_classe(self):
        sans_classe = Utilisateur.objects.create_user("orphelin", password="x", role=Role.ELEVE)
        self.client.force_login(sans_classe)
        reponse = self.client.get(reverse(URL))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Aucune classe")

    def test_nombre_de_requetes_constant(self):
        for jour in range(1, 6):
            Seance.objects.create(affectation=self.aff_a if jour % 2 else self.aff_a_fr,
                                  date=date(2026, 10, jour), titre=f"S{jour}", travail_a_faire="x")
        with self.assertNumQueries(7):  # session + utilisateur + séances + travaux + plans + notifications + classe
            self.client.get(reverse(URL))
