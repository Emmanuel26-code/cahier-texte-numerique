"""Tâche 49 : contenu du tableau de bord élève (ce qu'il voit, ce qu'il ne doit PAS voir)."""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.academique.models import Affectation, Classe, Matiere
from apps.cahier.models import Seance
from apps.plans.models import Plan
from apps.comptes.models import Utilisateur

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.academique.models import AnneeScolaire, Inscription
from apps.documents.models import Document

MEDIA_TEST = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(MEDIA_TEST, ignore_errors=True)


def annee():
    return AnneeScolaire.objects.get_or_create(
        libelle="2026-2027", defaults={"date_debut": date(2026, 9, 1), "date_fin": date(2027, 7, 31)})[0]


def utilisateur(nom, classe=None, **kw):
    """Crée un utilisateur (e-mail unique) et l'inscrit dans sa classe si besoin."""
    kw.setdefault("password", "x")
    u = Utilisateur.objects.create_user(nom, email=f"{nom}@exemple.ci", **kw)
    if classe is not None:
        Inscription.objects.create(eleve=u, classe=classe)
    return u


def creer_plan(affectation, titre, statut):
    """Un plan est rattaché à son affectation via un document importé."""
    doc = Document.objects.create(affectation=affectation, chapitre=titre,
                                  fichier=SimpleUploadedFile("cours.txt", b"contenu du cours"))
    return Plan.objects.create(document=doc, statut=statut)

Role = Utilisateur.Role
URL = "tableau_de_bord:eleve"


@override_settings(MEDIA_ROOT=MEDIA_TEST)
class TableauDeBordEleveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.classe_a = Classe.objects.create(nom="6e A", annee=annee())
        cls.classe_b = Classe.objects.create(nom="5e B", annee=annee())
        maths = Matiere.objects.create(nom="Mathématiques")
        francais = Matiere.objects.create(nom="Français")
        prof = utilisateur("prof", role=Role.PROFESSEUR)
        cls.aff_a = Affectation.objects.create(professeur=prof, classe=cls.classe_a, matiere=maths)
        cls.aff_a_fr = Affectation.objects.create(professeur=prof, classe=cls.classe_a, matiere=francais)
        cls.aff_b = Affectation.objects.create(professeur=prof, classe=cls.classe_b, matiere=maths)
        cls.eleve = utilisateur("eleve", role=Role.ELEVE, classe=cls.classe_a, first_name="Awa")

    def setUp(self):
        self.client.force_login(self.eleve)

    def test_affiche_travail_a_faire_et_seances_de_sa_classe(self):
        Seance.objects.create(affectation=self.aff_a, duree_minutes=60, date_seance=date(2026, 10, 12), titre="Addition de fractions",
                              travail_a_faire="Exercices 4 à 7, page 52")
        reponse = self.client.get(reverse(URL))
        self.assertContains(reponse, "Exercices 4 à 7, page 52")
        self.assertContains(reponse, "Addition de fractions")
        self.assertContains(reponse, "Bonjour, Awa")

    def test_ne_montre_pas_les_seances_des_autres_classes(self):
        Seance.objects.create(affectation=self.aff_b, duree_minutes=60, date_seance=date(2026, 10, 12), titre="Séance de la 5e B",
                              travail_a_faire="Devoir de la 5e B")
        reponse = self.client.get(reverse(URL))
        self.assertNotContains(reponse, "Séance de la 5e B")
        self.assertNotContains(reponse, "Devoir de la 5e B")

    def test_seance_sans_travail_n_apparait_pas_dans_travail_a_faire(self):
        Seance.objects.create(affectation=self.aff_a, duree_minutes=60, date_seance=date(2026, 10, 12), titre="Cours sans devoir")
        reponse = self.client.get(reverse(URL))
        self.assertEqual(reponse.context["travaux"], [])
        self.assertEqual(len(reponse.context["seances"]), 1)

    def test_seances_triees_de_la_plus_recente_a_la_plus_ancienne(self):
        for jour in (8, 12, 9):
            Seance.objects.create(affectation=self.aff_a, duree_minutes=60, date_seance=date(2026, 10, jour), titre=f"S{jour}")
        dates = [s.date_seance.day for s in self.client.get(reverse(URL)).context["seances"]]
        self.assertEqual(dates, [12, 9, 8])

    def test_limite_a_cinq_elements(self):
        for jour in range(1, 9):
            Seance.objects.create(affectation=self.aff_a, duree_minutes=60, date_seance=date(2026, 10, jour), titre=f"S{jour}",
                                  travail_a_faire="à faire")
        contexte = self.client.get(reverse(URL)).context
        self.assertEqual(len(contexte["seances"]), 5)
        self.assertEqual(len(contexte["travaux"]), 5)

    def test_seuls_les_plans_valides_sont_visibles(self):
        creer_plan(self.aff_a, "Plan validé", Plan.Statut.VALIDE)
        creer_plan(self.aff_a, "Plan proposé", Plan.Statut.PROPOSE)
        creer_plan(self.aff_a, "Plan rejeté", Plan.Statut.REJETE)
        creer_plan(self.aff_b, "Plan validé autre classe", Plan.Statut.VALIDE)
        reponse = self.client.get(reverse(URL))
        self.assertContains(reponse, "Plan validé")
        self.assertNotContains(reponse, "Plan proposé")
        self.assertNotContains(reponse, "Plan rejeté")
        self.assertNotContains(reponse, "autre classe")

    def test_messages_quand_il_n_y_a_rien(self):
        reponse = self.client.get(reverse(URL))
        self.assertContains(reponse, "Aucun travail à faire pour le moment.")
        self.assertContains(reponse, "Aucune séance enregistrée.")
        self.assertContains(reponse, "Aucun plan de cours publié.")

    def test_eleve_sans_classe(self):
        sans_classe = utilisateur("orphelin", role=Role.ELEVE)
        self.client.force_login(sans_classe)
        reponse = self.client.get(reverse(URL))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Aucune classe")

    def test_nombre_de_requetes_constant(self):
        for jour in range(1, 6):
            Seance.objects.create(affectation=self.aff_a if jour % 2 else self.aff_a_fr,
                                  duree_minutes=60, date_seance=date(2026, 10, jour), titre=f"S{jour}", travail_a_faire="x")
        with self.assertNumQueries(8):  # session + utilisateur + classes + séances + travaux + plans + notifications + année (context processor)
            self.client.get(reverse(URL))
