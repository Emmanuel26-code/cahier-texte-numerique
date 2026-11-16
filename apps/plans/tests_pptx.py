"""Lecture des présentations PowerPoint et contrôle des fichiers Office à l'import."""
import io
import zipfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.documents.validators import valider_contenu
from apps.plans.services.erreurs import ExtractionError
from apps.plans.services.extraction import extraire_texte

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def diapo(titre, puces):
    def forme(textes, titre=False):
        ph = '<p:nvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>' if titre else "<p:nvSpPr><p:nvPr/></p:nvSpPr>"
        paras = "".join(f"<a:p><a:r><a:t>{t}</a:t></a:r></a:p>" for t in textes)
        return f"<p:sp>{ph}<p:txBody>{paras}</p:txBody></p:sp>"
    return (f'<p:sld xmlns:a="{A}" xmlns:p="{P}"><p:cSld><p:spTree>'
            f"{forme([titre], titre=True)}{forme(puces)}</p:spTree></p:cSld></p:sld>").encode()


def fabriquer(parties):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        for nom, contenu in parties.items():
            archive.writestr(nom, contenu)
    return tampon.getvalue()


def presentation(macros=False):
    parties = {
        "[Content_Types].xml": "<Types/>",
        "ppt/presentation.xml": "<p:presentation/>",
        "ppt/slides/slide2.xml": diapo("Chapitre 2 : Les limites", ["Limite finie"]),
        "ppt/slides/slide1.xml": diapo("Chapitre 1 : Les suites", ["Définition", "Exemples"]),
    }
    if macros:
        parties["ppt/vbaProject.bin"] = b"\x00"
    return fabriquer(parties)


class LecturePowerPointTests(SimpleTestCase):
    def test_titres_des_diapositives_dans_l_ordre(self):
        texte = extraire_texte(io.BytesIO(presentation()), "cours.pptx")
        self.assertEqual(texte.splitlines()[0], "# Chapitre 1 : Les suites")
        self.assertIn("Définition", texte)
        self.assertLess(texte.index("Chapitre 1"), texte.index("Chapitre 2"))  # diapo 1 avant diapo 2

    def test_fichier_corrompu(self):
        with self.assertRaises(ExtractionError):
            extraire_texte(io.BytesIO(b"pas un zip"), "cours.pptx")


class ControleOfficeTests(SimpleTestCase):
    def verifier(self, nom, contenu):
        valider_contenu(SimpleUploadedFile(nom, contenu))

    def test_vraie_presentation_acceptee(self):
        self.verifier("cours.pptx", presentation())

    def test_faux_pptx_refuse(self):
        with self.assertRaises(ValidationError):
            self.verifier("cours.pptx", b"MZ\x90\x00 programme renomme")

    def test_classeur_sans_partie_excel_refuse(self):
        with self.assertRaises(ValidationError):
            self.verifier("notes.xlsx", fabriquer({"[Content_Types].xml": "<Types/>"}))

    def test_macros_refusees(self):
        with self.assertRaisesMessage(ValidationError, "macros"):
            self.verifier("cours.pptx", presentation(macros=True))
