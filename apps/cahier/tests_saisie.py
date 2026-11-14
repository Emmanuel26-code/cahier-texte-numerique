"""Saisie des séances : création, modification (avec historique) et suppression logique."""
import datetime

from django.test import TestCase
from django.urls import reverse

from apps.academique.models import Affectation, AnneeScolaire, Classe, Inscription, Matiere
from apps.cahier.models import Seance, SeanceHistorique
from apps.comptes.models import Utilisateur
from apps.documents.models import Document
from apps.notifications.models import Notification
from apps.plans.models import Plan, Titre

Role = Utilisateur.Role


def utilisateur(nom, role, **kw):
    return Utilisateur.objects.create_user(nom, f"{nom}@exemple.ci", "MotDePasse-Solide-2026", role=role, **kw)


class SaisieSeanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        annee = AnneeScolaire.objects.create(
            libelle="2026-2027", date_debut=datetime.date(2026, 9, 1), date_fin=datetime.date(2027, 7, 31))
        cls.classe = Classe.objects.create(nom="Tle D", annee=annee)
        maths = Matiere.objects.create(nom="Maths")
        cls.prof = utilisateur("prof", Role.PROFESSEUR)
        cls.autre_prof = utilisateur("autre", Role.PROFESSEUR)
        cls.admin = utilisateur("admin1", Role.ADMINISTRATEUR)
        cls.eleve = utilisateur("eleve", Role.ELEVE)
        Inscription.objects.create(eleve=cls.eleve, classe=cls.classe)
        cls.aff = Affectation.objects.create(professeur=cls.prof, classe=cls.classe, matiere=maths)
        cls.aff_autre = Affectation.objects.create(
            professeur=cls.autre_prof, classe=cls.classe, matiere=Matiere.objects.create(nom="SVT"))

    def donnees(self, **kw):
        base = {
            "affectation": self.aff.pk, "date_seance": "2026-10-12", "duree_minutes": 60,
            "titre": "Les suites", "contenu_traite": "Définition et exemples", "travail_a_faire": "",
        }
        base.update(kw)
        return base

    def seance(self, **kw):
        kw.setdefault("affectation", self.aff)
        return Seance.objects.create(date_seance=datetime.date(2026, 10, 12), duree_minutes=60,
                                     titre="Séance", contenu_traite="Contenu", **kw)

    # --- création
    def test_professeur_cree_une_seance(self):
        self.client.force_login(self.prof)
        reponse = self.client.post(reverse("cahier:creer"), self.donnees(travail_a_faire="Exercice 3"))
        seance = Seance.objects.get(titre="Les suites")
        self.assertRedirects(reponse, reverse("cahier:detail", args=[seance.pk]))
        # le travail à faire déclenche la notification de l'élève de la classe
        self.assertEqual(Notification.objects.filter(destinataire=self.eleve).count(), 1)

    def test_professeur_ne_peut_pas_saisir_pour_l_affectation_d_un_autre(self):
        self.client.force_login(self.prof)
        reponse = self.client.post(reverse("cahier:creer"), self.donnees(affectation=self.aff_autre.pk))
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Seance.objects.exists())

    def test_eleve_ne_peut_pas_creer(self):
        self.client.force_login(self.eleve)
        self.assertEqual(self.client.get(reverse("cahier:creer")).status_code, 403)

    def test_duree_invalide_refusee(self):
        self.client.force_login(self.prof)
        self.client.post(reverse("cahier:creer"), self.donnees(duree_minutes=0))
        self.assertFalse(Seance.objects.exists())

    def test_points_du_plan_d_une_autre_affectation_refuses(self):
        doc = Document.objects.create(affectation=self.aff_autre, nom_original="c.pdf", fichier="documents/c.pdf",
                                      type_mime="application/pdf", taille_octets=1)
        plan = Plan.objects.create(document=doc, statut=Plan.Statut.VALIDE)
        point = Titre.objects.create(plan=plan, niveau=1, ordre=1, libelle="Génétique")
        self.client.force_login(self.admin)
        self.client.post(reverse("cahier:creer"), self.donnees(points_du_plan=[point.pk]))
        self.assertFalse(Seance.objects.exists())

    # --- modification
    def test_modification_conserve_l_ancienne_version(self):
        seance = self.seance()
        self.client.force_login(self.prof)
        self.client.post(reverse("cahier:modifier", args=[seance.pk]), self.donnees(titre="Titre corrigé"))
        seance.refresh_from_db()
        self.assertEqual(seance.titre, "Titre corrigé")
        entree = SeanceHistorique.objects.get(seance=seance)
        self.assertEqual(entree.action, SeanceHistorique.Action.MODIFICATION)
        self.assertEqual(entree.anciennes_valeurs["titre"], "Séance")
        self.assertEqual(entree.modifie_par, self.prof)

    def test_autre_professeur_ne_peut_pas_modifier(self):
        seance = self.seance()
        self.client.force_login(self.autre_prof)
        self.assertEqual(self.client.get(reverse("cahier:modifier", args=[seance.pk])).status_code, 404)

    def test_administrateur_peut_modifier(self):
        seance = self.seance()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("cahier:modifier", args=[seance.pk])).status_code, 200)

    # --- suppression
    def test_suppression_logique_et_historisee(self):
        seance = self.seance()
        self.client.force_login(self.prof)
        reponse = self.client.post(reverse("cahier:supprimer", args=[seance.pk]))
        self.assertRedirects(reponse, reverse("cahier:liste"))
        seance.refresh_from_db()
        self.assertTrue(seance.supprime)
        self.assertTrue(SeanceHistorique.objects.filter(seance=seance, action="suppression").exists())
        self.assertNotContains(self.client.get(reverse("cahier:liste")), "Séance</strong>")

    def test_suppression_refuse_get(self):
        seance = self.seance()
        self.client.force_login(self.prof)
        self.assertEqual(self.client.get(reverse("cahier:supprimer", args=[seance.pk])).status_code, 405)

    def test_detail_montre_les_boutons_au_proprietaire_seulement(self):
        seance = self.seance()
        self.client.force_login(self.prof)
        self.assertContains(self.client.get(reverse("cahier:detail", args=[seance.pk])), "Modifier")
        self.client.force_login(self.eleve)
        self.assertNotContains(self.client.get(reverse("cahier:detail", args=[seance.pk])),
                               reverse("cahier:modifier", args=[seance.pk]))
