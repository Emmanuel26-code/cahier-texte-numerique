import datetime

from django.test import TestCase

from apps.academique.models import Affectation, AnneeScolaire, Classe, Inscription, Matiere
from apps.cahier.models import Seance, SeanceHistorique
from apps.comptes.models import Utilisateur
from apps.documents.models import Document
from apps.plans.models import Plan, Titre


class ModeleDonneesTests(TestCase):
    def test_chaine_complete_du_modele(self):
        prof = Utilisateur.objects.create_user("prof", "p@x.ci", "x" * 12, role="professeur")
        eleve = Utilisateur.objects.create_user("eleve", "e@x.ci", "x" * 12, role="eleve")
        annee = AnneeScolaire.objects.create(libelle="2026-2027", date_debut=datetime.date(2026, 9, 1), date_fin=datetime.date(2027, 6, 30))
        classe = Classe.objects.create(nom="Terminale D", annee=annee)
        Inscription.objects.create(eleve=eleve, classe=classe)
        aff = Affectation.objects.create(professeur=prof, classe=classe, matiere=Matiere.objects.create(nom="Physique"))
        doc = Document.objects.create(affectation=aff, nom_original="cours.pdf", fichier="documents/cours.pdf", type_mime="application/pdf", taille_octets=10)
        plan = Plan.objects.create(document=doc)
        partie = Titre.objects.create(plan=plan, niveau=1, ordre=1, libelle="Mécanique")
        chap = Titre.objects.create(plan=plan, parent=partie, niveau=2, ordre=1, libelle="Cinématique")
        seance = Seance.objects.create(affectation=aff, date_seance=datetime.date(2026, 10, 12), duree_minutes=120, titre="Intro", contenu_traite="...")
        seance.points_du_plan.add(chap)
        SeanceHistorique.objects.create(seance=seance, modifie_par=prof, action="modification", anciennes_valeurs={"titre": "Ancien"})

        self.assertEqual(list(partie.enfants.all()), [chap])
        self.assertEqual(list(classe.eleves.all()), [eleve])
        self.assertEqual(chap.seances.count(), 1)
        self.assertEqual(seance.historique.count(), 1)
