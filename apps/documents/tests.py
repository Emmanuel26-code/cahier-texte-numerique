import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.academique.models import Affectation, AnneeScolaire, Classe, Matiere
from apps.comptes.models import Utilisateur

from .models import Document
from .validators import TAILLE_MAX_OCTETS

DOSSIER_TEST = tempfile.mkdtemp()  # les fichiers de test vont ici, pas dans media/


@override_settings(MEDIA_ROOT=DOSSIER_TEST)
class ImportDocumentTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(DOSSIER_TEST, ignore_errors=True)

    def setUp(self):
        self.prof = Utilisateur.objects.create_user("prof1", "p1@example.com", "MotDePasse-Solide-2026", role="professeur")
        annee = AnneeScolaire.objects.create(
            libelle="2026-2027",
            date_debut=datetime.date(2026, 9, 1),
            date_fin=datetime.date(2027, 6, 30),
        )
        classe = Classe.objects.create(nom="Terminale D", annee=annee)
        matiere = Matiere.objects.create(nom="Physique")
        self.aff = Affectation.objects.create(
            professeur=self.prof, classe=classe, matiere=matiere
        )
        self.client.login(username="prof1", password="MotDePasse-Solide-2026")

    def envoyer(self, nom, contenu, affectation=None):
        return self.client.post(
            "/documents/importer/",
            {
                "fichier": SimpleUploadedFile(nom, contenu),
                "chapitre": "Chapitre 1",
                "affectation": (affectation or self.aff).pk,
            },
        )

    def test_import_txt_accepte(self):
        reponse = self.envoyer("cours.txt", b"Introduction\nPartie 1")
        self.assertRedirects(reponse, "/documents/")
        doc = Document.objects.get()
        self.assertEqual(doc.nom_original, "cours.txt")
        self.assertEqual(doc.type_mime, "text/plain")
        self.assertEqual(doc.taille_octets, len(b"Introduction\nPartie 1"))

    def test_import_pdf_et_docx_acceptes(self):
        self.envoyer("cours.pdf", b"%PDF-1.4 contenu")
        self.envoyer("cours.docx", b"PK contenu")
        self.assertEqual(Document.objects.count(), 2)

    def test_format_non_autorise_refuse(self):
        self.envoyer("virus.exe", b"MZ contenu")
        self.assertEqual(Document.objects.count(), 0)

    def test_fichier_trop_gros_refuse(self):
        self.envoyer("gros.pdf", b"x" * (TAILLE_MAX_OCTETS + 1))
        self.assertEqual(Document.objects.count(), 0)

    def test_fichier_exactement_10_mo_accepte(self):
        self.envoyer("limite.pdf", b"x" * TAILLE_MAX_OCTETS)
        self.assertEqual(Document.objects.count(), 1)

    def test_connexion_obligatoire(self):
        self.client.logout()
        reponse = self.client.get("/documents/importer/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/comptes/connexion/", reponse["Location"])
    
    def test_affectation_d_un_autre_professeur_refusee(self):
        autre = Utilisateur.objects.create_user("prof2", "p2@example.com", "MotDePasse-Solide-2026", role="professeur")
        aff_autre = Affectation.objects.create(professeur=autre, classe=self.aff.classe, matiere=self.aff.matiere)
        self.envoyer("cours.pdf", b"%PDF-1.4 contenu", affectation=aff_autre)
        self.assertEqual(Document.objects.count(), 0)