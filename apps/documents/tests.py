import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

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
        Utilisateur.objects.create_user("prof1", "p1@example.com", "MotDePasse-Solide-2026", role="professeur")
        self.client.login(username="prof1", password="MotDePasse-Solide-2026")

    def envoyer(self, nom, contenu):
        return self.client.post(
            "/documents/importer/",
            {"fichier": SimpleUploadedFile(nom, contenu), "chapitre": "Chapitre 1"},
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