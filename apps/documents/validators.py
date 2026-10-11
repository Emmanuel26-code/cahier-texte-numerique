import os
import zipfile

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

EXTENSIONS_AUTORISEES = ["docx", "pdf", "txt", "pptx", "xlsx"]
TAILLE_MAX_OCTETS = 10 * 1024 * 1024  # 10 Mo

MAX_DECOMPRESSE_OCTETS = 100 * 1024 * 1024  
MAX_ENTREES_ZIP = 2000

valider_extension = FileExtensionValidator(
    allowed_extensions=EXTENSIONS_AUTORISEES,
    message="Format non accepté. Formats autorisés : DOCX, PDF, TXT, PPTX, XLSX.",
)


def valider_taille(fichier):
    """Refuse les fichiers de plus de 10 Mo."""
    if fichier.size > TAILLE_MAX_OCTETS:
        raise ValidationError("Fichier trop volumineux. Taille maximale : 10 Mo.")


def _verifier_docx(fichier):
    try:
        with zipfile.ZipFile(fichier) as archive:
            noms = archive.namelist()
            infos = archive.infolist()
    except zipfile.BadZipFile:
        raise ValidationError("Ce fichier n'est pas un vrai document Word (DOCX).")

    if "[Content_Types].xml" not in noms or "word/document.xml" not in noms:
        raise ValidationError("Ce fichier n'est pas un vrai document Word (DOCX).")
    if len(noms) > MAX_ENTREES_ZIP or sum(i.file_size for i in infos) > MAX_DECOMPRESSE_OCTETS:
        raise ValidationError("Ce document Word est anormalement volumineux une fois décompressé.")


def valider_contenu(fichier):
    """Vérifie que le CONTENU du fichier correspond à son extension.

    Un fichier .exe renommé en .pdf a la bonne extension mais pas le bon contenu :
    on regarde donc les premiers octets ("signature") du fichier.
    """
    extension = os.path.splitext(fichier.name)[1].lower().lstrip(".")
    fichier.seek(0)
    debut = fichier.read(8192)
    fichier.seek(0)

    if extension == "pdf":
        if not debut.startswith(b"%PDF-"):
            raise ValidationError("Ce fichier n'est pas un vrai PDF.")
    elif extension == "docx":
        _verifier_docx(fichier)
    elif extension == "txt":
        if b"\x00" in debut:  
            raise ValidationError("Ce fichier n'est pas un fichier texte valide.")

    fichier.seek(0)