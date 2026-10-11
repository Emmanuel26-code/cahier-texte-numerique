from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

EXTENSIONS_AUTORISEES = ["docx", "pdf", "pptx", "xlsx", "txt"]
TAILLE_MAX_OCTETS = 10 * 1024 * 1024  # 10 Mo

valider_extension = FileExtensionValidator(
    allowed_extensions=EXTENSIONS_AUTORISEES,
    message="Format non accepté. Formats autorisés : DOCX, XLSX, PPTX, TXT, PDF.",
)


def valider_taille(fichier):
    """Refuse les fichiers de plus de 10 Mo."""
    if fichier.size > TAILLE_MAX_OCTETS:
        raise ValidationError("Fichier trop volumineux. Taille maximale : 10 Mo.")