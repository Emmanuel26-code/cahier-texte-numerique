import datetime

from django.test import TestCase
import datetime

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


class HistoriquePageTests(TestCase):
    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            "admin-history", "admin-history@example.com", "MotDePasse-Solide-2026",
            role=Utilisateur.Role.ADMINISTRATEUR,
        )
        self.prof = Utilisateur.objects.create_user(
            "prof-history", "prof-history@example.com", "MotDePasse-Solide-2026",
            role=Utilisateur.Role.PROFESSEUR,
        )
        annee = AnneeScolaire.objects.create(
            libelle="2026-2027",
            date_debut=datetime.date(2026, 9, 1),
            date_fin=datetime.date(2027, 8, 31),
        )
        self.classe = Classe.objects.create(nom="6e A", annee=annee)
        affectation = Affectation.objects.create(
            professeur=self.prof, classe=self.classe, matiere=Matiere.objects.create(nom="Français")
        )
        seance = Seance.objects.create(
            affectation=affectation,
            date_seance=datetime.date(2026, 10, 9),
            duree_minutes=50,
            titre="Lecture",
            contenu_traite="Lecture suivie",
        )
        self.entree = SeanceHistorique.objects.create(
            seance=seance,
            modifie_par=self.prof,
            action=SeanceHistorique.Action.MODIFICATION,
            anciennes_valeurs={"duree_minutes": 45},
        )

    def test_historique_affiche_entrees_et_anciennes_valeurs(self):
        self.client.force_login(self.admin)
        response = self.client.get(f"/cahier/historique/?detail={self.entree.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historique des modifications")
        self.assertContains(response, "45")

    def test_historique_refuse_aux_non_administrateurs(self):
        self.client.force_login(self.prof)
        self.assertEqual(self.client.get("/cahier/historique/").status_code, 403)

    def test_seances_sont_filtrees_selon_le_role_et_consultables(self):
        self.client.force_login(self.prof)
        self.assertContains(self.client.get("/cahier/"), "Lecture")
        self.assertContains(self.client.get(f"/cahier/seances/{self.entree.seance_id}/"), "Lecture suivie")

        eleve = Utilisateur.objects.create_user(
            "eleve-history", "eleve-history@example.com", "MotDePasse-Solide-2026",
            role=Utilisateur.Role.ELEVE,
        )
        self.client.force_login(eleve)
        self.assertNotContains(self.client.get("/cahier/"), "Lecture")
        self.assertEqual(
            self.client.get(f"/cahier/seances/{self.entree.seance_id}/").status_code,
            404,
        )

        Inscription.objects.create(eleve=eleve, classe=self.classe)
        self.assertContains(self.client.get("/cahier/"), "Lecture")
