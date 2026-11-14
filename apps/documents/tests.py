import io
import os
import re
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.comptes.models import Utilisateur
from apps.plans.tests import creer_affectation

from .models import Document, nettoyer_nom
from django.conf import settings

TAILLE_MAX_OCTETS = settings.DOCUMENT_MAX_OCTETS

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

    def test_administrateur_peut_importer_sur_une_affectation(self):
        administrateur = Utilisateur.objects.create_user(
            "admin-import", "admin-import@example.com", "MotDePasse-Solide-2026",
            role="administrateur",
        )
        self.client.force_login(administrateur)
        reponse = self.envoyer("cours-admin.txt", b"Support de cours")
        self.assertRedirects(reponse, "/documents/")
        self.assertEqual(Document.objects.get().affectation, self.affectation)

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
    
    # --- Rattachement à une affectation ------------------------------------------
    def test_affectation_obligatoire(self):
        reponse = self.client.post(
            "/documents/importer/",
            {"fichier": SimpleUploadedFile("cours.txt", b"contenu"), "chapitre": "Chapitre 1"},
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(Document.objects.count(), 0)

    def test_affectation_d_un_autre_professeur_refusee(self):
        autre = creer_affectation("prof2")
        reponse = self.envoyer("cours.txt", b"contenu", affectation=autre)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(Document.objects.count(), 0)

    def test_document_rattache_a_l_affectation_choisie(self):
        self.envoyer("cours.txt", b"contenu")
        self.assertEqual(Document.objects.get().affectation, self.affectation)

    def test_la_liste_ne_montre_que_les_documents_du_professeur(self):
        autre = creer_affectation("prof2")
        mien = Document.objects.create(
            affectation=self.affectation, nom_original="a.txt", fichier="documents/a.txt",
            type_mime="text/plain", taille_octets=1,
        )
        Document.objects.create(
            affectation=autre, nom_original="b.txt", fichier="documents/b.txt",
            type_mime="text/plain", taille_octets=1,
        )
        reponse = self.client.get("/documents/")
        self.assertEqual(list(reponse.context["documents"]), [mien])

@override_settings(MEDIA_ROOT=DOSSIER_TEST)
class TelechargementProtegeTests(TestCase):
    """Les fichiers ne sont envoyés qu'aux personnes autorisées."""

    def setUp(self):
        from apps.academique.models import Inscription

        self.affectation = creer_affectation("prof-dl")
        self.document = Document.objects.create(
            affectation=self.affectation, chapitre="Ch. 1",
            fichier=SimpleUploadedFile("cours.pdf", PDF_VALIDE),
        )
        self.url = f"/documents/{self.document.pk}/telecharger/"
        self.eleve = Utilisateur.objects.create_user("eleve-dl", "eleve-dl@example.com", "x" * 12, role="eleve")
        Inscription.objects.create(eleve=self.eleve, classe=self.affectation.classe)

    def test_professeur_proprietaire_telecharge(self):
        self.client.force_login(self.affectation.professeur)
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(b"".join(reponse.streaming_content), PDF_VALIDE)
        self.assertIn('attachment; filename="cours.pdf"', reponse["Content-Disposition"])

    def test_eleve_de_la_classe_telecharge(self):
        self.client.force_login(self.eleve)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_autres_refuses(self):
        autre_prof = Utilisateur.objects.create_user("autre-dl", "autre-dl@example.com", "x" * 12, role="professeur")
        autre_eleve = Utilisateur.objects.create_user("ailleurs-dl", "ailleurs@example.com", "x" * 12, role="eleve")
        for compte in (autre_prof, autre_eleve):
            self.client.force_login(compte)
            self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_visiteur_redirige_vers_la_connexion(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_aucune_adresse_media_publique(self):
        self.client.force_login(self.affectation.professeur)
        self.assertEqual(self.client.get(f"/media/{self.document.fichier.name}").status_code, 404)
