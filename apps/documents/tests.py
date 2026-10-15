import io
import os
import re
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.plans.tests import creer_affectation

from .models import Document, nettoyer_nom
from .validators import TAILLE_MAX_OCTETS

DOSSIER_TEST = tempfile.mkdtemp()  # les fichiers de test vont ici, pas dans media/

PDF_VALIDE = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


def faux_docx(avec_document=True, remplissage=0):
    """Fabrique un petit DOCX valide (une archive ZIP avec les bons fichiers)."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        if avec_document:
            archive.writestr("word/document.xml", "<w:document/>")
        if remplissage:
            archive.writestr("word/gros.xml", b"0" * remplissage)
    return tampon.getvalue()


@override_settings(MEDIA_ROOT=DOSSIER_TEST)
class ImportDocumentTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(DOSSIER_TEST, ignore_errors=True)

    def setUp(self):
        self.affectation = creer_affectation("prof1")
        self.client.force_login(self.affectation.professeur)

    def envoyer(self, nom, contenu, affectation=None):
        affectation = affectation or self.affectation
        return self.client.post(
            "/documents/importer/",
            {
                "affectation": affectation.pk,
                "fichier": SimpleUploadedFile(nom, contenu),
                "chapitre": "Chapitre 1",
            },
        )

    # --- Tâche 36 : format et taille ---------------------------------------
    def test_import_txt_accepte(self):
        reponse = self.envoyer("cours.txt", b"Introduction\nPartie 1")
        self.assertRedirects(reponse, "/documents/")
        doc = Document.objects.get()
        self.assertEqual(doc.nom_original, "cours.txt")
        self.assertEqual(doc.type_mime, "text/plain")
        self.assertEqual(doc.taille_octets, len(b"Introduction\nPartie 1"))

    def test_import_pdf_et_docx_acceptes(self):
        self.envoyer("cours.pdf", PDF_VALIDE)
        self.envoyer("cours.docx", faux_docx())
        self.assertEqual(Document.objects.count(), 2)

    def test_format_non_autorise_refuse(self):
        self.envoyer("virus.exe", b"MZ contenu")
        self.assertEqual(Document.objects.count(), 0)

    def test_fichier_trop_gros_refuse(self):
        self.envoyer("gros.pdf", PDF_VALIDE + b"x" * TAILLE_MAX_OCTETS)
        self.assertEqual(Document.objects.count(), 0)

    def test_fichier_exactement_10_mo_accepte(self):
        contenu = PDF_VALIDE + b"x" * (TAILLE_MAX_OCTETS - len(PDF_VALIDE))
        self.assertEqual(len(contenu), TAILLE_MAX_OCTETS)
        self.envoyer("limite.pdf", contenu)
        self.assertEqual(Document.objects.count(), 1)

    def test_connexion_obligatoire(self):
        self.client.logout()
        reponse = self.client.get("/documents/importer/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/comptes/connexion/", reponse["Location"])

    # --- Tâche 37 : contenu réel du fichier -----------------------------------
    def test_executable_renomme_en_pdf_refuse(self):
        self.envoyer("facture.pdf", b"MZ\x90\x00\x03\x00\x00\x00 programme windows")
        self.assertEqual(Document.objects.count(), 0)

    def test_faux_docx_refuse(self):
        self.envoyer("cours.docx", b"PK contenu qui n'est pas une archive")
        self.assertEqual(Document.objects.count(), 0)

    def test_archive_zip_sans_contenu_word_refusee(self):
        self.envoyer("cours.docx", faux_docx(avec_document=False))
        self.assertEqual(Document.objects.count(), 0)

    def test_txt_binaire_refuse(self):
        self.envoyer("notes.txt", b"abc\x00\x01\x02def")
        self.assertEqual(Document.objects.count(), 0)

    def test_bombe_zip_refusee(self):
        with patch("apps.documents.validators.MAX_DECOMPRESSE_OCTETS", 1000):
            self.envoyer("bombe.docx", faux_docx(remplissage=5000))
        self.assertEqual(Document.objects.count(), 0)

    # --- Tâche 37 : noms de fichiers -------------------------------------------
    def test_nom_affiche_nettoye_et_nom_disque_aleatoire(self):
        self.envoyer("mon cours (v2)!.txt", b"contenu")
        doc = Document.objects.get()
        self.assertEqual(doc.nom_original, "mon_cours_v2.txt")
        self.assertRegex(doc.fichier.name, r"^documents/\d{4}/\d{2}/[0-9a-f]{32}\.txt$")
        self.assertTrue(os.path.exists(doc.fichier.path))

    def test_extension_en_majuscules_acceptee_et_normalisee(self):
        self.envoyer("COURS.PDF", PDF_VALIDE)
        doc = Document.objects.get()
        self.assertTrue(doc.fichier.name.endswith(".pdf"))

    def test_nettoyer_nom_supprime_les_chemins(self):
        self.assertEqual(nettoyer_nom("../../etc/passwd.txt"), "passwd.txt")
        self.assertEqual(nettoyer_nom("C:\\Users\\Moi\\cours final.pdf"), "cours_final.pdf")