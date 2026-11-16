"""Relecture, correction et validation d'un plan proposé par l'IA."""
import datetime

from django.test import TestCase
from django.urls import reverse

from apps.academique.models import Affectation, AnneeScolaire, Classe, Inscription, Matiere
from apps.comptes.models import Utilisateur
from apps.documents.models import Document
from apps.notifications.models import Notification
from apps.plans.models import Plan, Titre

Role = Utilisateur.Role


def utilisateur(nom, role):
    return Utilisateur.objects.create_user(nom, f"{nom}@exemple.ci", "MotDePasse-Solide-2026", role=role)


class ValidationPlanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        annee = AnneeScolaire.objects.create(
            libelle="2026-2027", date_debut=datetime.date(2026, 9, 1), date_fin=datetime.date(2027, 7, 31))
        classe = Classe.objects.create(nom="1re C", annee=annee)
        cls.prof = utilisateur("prof", Role.PROFESSEUR)
        cls.autre_prof = utilisateur("autre", Role.PROFESSEUR)
        cls.eleve = utilisateur("eleve", Role.ELEVE)
        cls.eleve_ailleurs = utilisateur("ailleurs", Role.ELEVE)
        Inscription.objects.create(eleve=cls.eleve, classe=classe)
        aff = Affectation.objects.create(professeur=cls.prof, classe=classe, matiere=Matiere.objects.create(nom="PC"))
        cls.document = Document.objects.create(
            affectation=aff, chapitre="Électricité", nom_original="elec.pdf", fichier="documents/elec.pdf",
            type_mime="application/pdf", taille_octets=1)

    def setUp(self):
        self.plan = Plan.objects.create(document=self.document)
        self.partie = Titre.objects.create(plan=self.plan, niveau=1, ordre=1, libelle="Courant continu")
        self.chapitre = Titre.objects.create(plan=self.plan, parent=self.partie, niveau=2, ordre=2, libelle="Loi d'Ohm")
        self.autre = Titre.objects.create(plan=self.plan, niveau=1, ordre=3, libelle="Hors sujet")
        self.url = reverse("plans:detail", args=[self.plan.pk])

    def test_professeur_corrige_retire_et_valide(self):
        self.client.force_login(self.prof)
        reponse = self.client.post(self.url, {
            "action": "valider",
            f"libelle_{self.partie.pk}": "Le courant continu",
            f"libelle_{self.chapitre.pk}": "Loi d'Ohm",
            f"libelle_{self.autre.pk}": "Hors sujet",
            "supprimer": [str(self.autre.pk)],
        })
        self.assertRedirects(reponse, self.url)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.statut, Plan.Statut.VALIDE)
        self.assertIsNotNone(self.plan.date_validation)
        self.assertEqual(list(self.plan.titres.values_list("libelle", flat=True)), ["Le courant continu", "Loi d'Ohm"])
        # la validation notifie les élèves de la classe
        self.assertEqual(Notification.objects.filter(destinataire=self.eleve).count(), 1)

    def test_retirer_une_partie_retire_ses_sous_points(self):
        self.client.force_login(self.prof)
        self.client.post(self.url, {"action": "enregistrer", "supprimer": [str(self.partie.pk)]})
        self.assertEqual(list(self.plan.titres.values_list("libelle", flat=True)), ["Hors sujet"])
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.statut, Plan.Statut.PROPOSE)

    def test_plan_vide_ne_peut_pas_etre_valide(self):
        self.client.force_login(self.prof)
        self.client.post(self.url, {"action": "valider",
                                    "supprimer": [str(self.partie.pk), str(self.autre.pk)]})
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.statut, Plan.Statut.PROPOSE)

    def test_rejeter(self):
        self.client.force_login(self.prof)
        self.client.post(self.url, {"action": "rejeter"})
        self.assertFalse(Plan.objects.filter(pk=self.plan.pk).exists())  # un plan rejeté est supprimé

    def test_autre_professeur_ne_voit_pas_le_plan(self):
        self.client.force_login(self.autre_prof)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"action": "valider"}).status_code, 404)

    def test_eleve_ne_voit_que_les_plans_valides_de_sa_classe(self):
        self.client.force_login(self.eleve)
        self.assertEqual(self.client.get(self.url).status_code, 404)  # encore « proposé »
        self.plan.statut = Plan.Statut.VALIDE
        self.plan.save()
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Loi d&#x27;Ohm")
        self.assertNotContains(reponse, "Valider le plan")
        self.assertEqual(self.client.post(self.url, {"action": "rejeter"}).status_code, 404)
        self.client.force_login(self.eleve_ailleurs)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_plan_valide_n_est_plus_modifiable(self):
        self.plan.statut = Plan.Statut.VALIDE
        self.plan.save()
        self.client.force_login(self.prof)
        self.assertEqual(self.client.post(self.url, {"action": "rejeter"}).status_code, 404)


class AvancementProgrammeTests(TestCase):
    """Part des points du plan validé déjà traités en séance."""

    @classmethod
    def setUpTestData(cls):
        from apps.cahier.models import Seance

        annee = AnneeScolaire.objects.create(
            libelle="2026-2027", date_debut=datetime.date(2026, 9, 1), date_fin=datetime.date(2027, 7, 31))
        classe = Classe.objects.create(nom="2nde A", annee=annee)
        cls.prof = utilisateur("prof-av", Role.PROFESSEUR)
        cls.eleve = utilisateur("eleve-av", Role.ELEVE)
        Inscription.objects.create(eleve=cls.eleve, classe=classe)
        aff = Affectation.objects.create(professeur=cls.prof, classe=classe, matiere=Matiere.objects.create(nom="Histoire"))
        document = Document.objects.create(affectation=aff, chapitre="Révolution", nom_original="r.pdf",
                                           fichier="documents/r.pdf", type_mime="application/pdf", taille_octets=1)
        cls.plan = Plan.objects.create(document=document, statut=Plan.Statut.VALIDE)
        cls.points = [Titre.objects.create(plan=cls.plan, niveau=1, ordre=i, libelle=f"Point {i}") for i in range(1, 5)]
        traitee = Seance.objects.create(affectation=aff, date_seance=datetime.date(2026, 10, 1), duree_minutes=55,
                                        titre="S1", contenu_traite="...")
        traitee.points_du_plan.add(cls.points[0])
        supprimee = Seance.objects.create(affectation=aff, date_seance=datetime.date(2026, 10, 2), duree_minutes=55,
                                          titre="S2", contenu_traite="...", supprime=True)
        supprimee.points_du_plan.add(cls.points[1])  # séance supprimée : ne compte pas

    def test_pourcentage_sur_le_tableau_de_bord_professeur(self):
        self.client.force_login(self.prof)
        self.assertContains(self.client.get("/tableau-de-bord/professeur/"), "Programme : 25 % (1/4)")

    def test_points_traites_marques_sur_le_plan(self):
        self.client.force_login(self.prof)
        page = self.client.get(f"/plans/{self.plan.pk}/").content.decode()
        self.assertEqual(page.count(">Traité</span>"), 1)

    def test_l_eleve_voit_l_avancement(self):
        self.client.force_login(self.eleve)
        self.assertContains(self.client.get("/tableau-de-bord/eleve/"), "Programme : 25 %")
