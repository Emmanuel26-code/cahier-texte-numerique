"""Extraction du texte d'un cours (DOCX, PDF, TXT) vers du Markdown léger.

Le but n'est pas de reproduire le document mais de donner à l'IA des indices
fiables sur la structure : les titres sont préfixés par des `#` (comme en
Markdown) quand on peut les reconnaître grâce aux styles Word ou à la taille des
caractères dans un PDF. Le LLM garde le dernier mot ; ces indices l'aident
seulement à ne pas deviner.
"""
import os
import re
import zipfile
from collections import Counter

from django.conf import settings

from .erreurs import ExtractionError

EXTENSIONS_ACCEPTEES = (".docx", ".pdf", ".txt")

_TITRE_COURT_MAX = 100  # au-delà, une ligne en gras est un paragraphe, pas un titre
_NIVEAU_TITRE_MAX = 4
_DOCX_DECOMPRESSE_MAX = 50 * 1024 * 1024  # un .docx est un zip : refuse les « zip bombs »


def extraire_texte(fichier, nom: str) -> str:
    """Retourne le texte d'un fichier ouvert en binaire (`fichier`) selon l'extension de `nom`."""
    extension = os.path.splitext(nom or "")[1].lower()
    if extension == ".docx":
        texte = _extraire_docx(fichier)
    elif extension == ".pdf":
        texte = _extraire_pdf(fichier, settings.IA_MAX_PAGES, settings.IA_MAX_CHARS)
    elif extension == ".txt":
        texte = _extraire_txt(fichier)
    else:
        formats = ", ".join(e.lstrip(".").upper() for e in EXTENSIONS_ACCEPTEES)
        raise ExtractionError(f"Format non pris en charge ({extension or 'inconnu'}). Formats acceptés : {formats}.")

    texte = texte.strip()
    if not texte:
        raise ExtractionError(
            "Aucun texte exploitable dans ce fichier (document vide, ou PDF scanné sans texte)."
        )
    return texte


# --- TXT -------------------------------------------------------------------

def _extraire_txt(fichier) -> str:
    brut = fichier.read()
    for encodage in ("utf-8-sig", "cp1252"):
        try:
            return brut.decode(encodage)
        except UnicodeDecodeError:
            continue
    return brut.decode("latin-1", errors="replace")


# --- DOCX ------------------------------------------------------------------

_STYLE_TITRE = re.compile(r"^(?:heading|titre)\s*(\d)$", re.IGNORECASE)
_STYLES_TITRE_DOCUMENT = {"title", "titre"}


def _niveau_titre_docx(nom_style: str):
    nom = (nom_style or "").strip()
    if nom.lower() in _STYLES_TITRE_DOCUMENT:
        return 1
    correspondance = _STYLE_TITRE.match(nom)
    if correspondance:
        return max(1, min(int(correspondance.group(1)), _NIVEAU_TITRE_MAX))
    return None


def _extraire_docx(fichier) -> str:
    from docx import Document as DocxDocument

    try:
        with zipfile.ZipFile(fichier) as archive:
            taille_decompressee = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as exc:
        raise ExtractionError("Impossible de lire ce fichier Word : il est corrompu ou protégé.") from exc
    if taille_decompressee > _DOCX_DECOMPRESSE_MAX:
        raise ExtractionError("Ce fichier Word est trop volumineux une fois décompressé pour être analysé.")
    fichier.seek(0)

    try:
        document = DocxDocument(fichier)
    except Exception as exc:  # fichier corrompu, protégé ou pas un vrai .docx
        raise ExtractionError("Impossible de lire ce fichier Word : il est corrompu ou protégé.") from exc

    lignes = []
    for paragraphe in document.paragraphs:
        texte = paragraphe.text.strip()
        if not texte:
            continue
        style = paragraphe.style.name if paragraphe.style is not None else ""
        niveau = _niveau_titre_docx(style)
        if niveau:
            lignes.append(f"{'#' * niveau} {texte}")
        elif _est_ligne_en_gras(paragraphe, texte):
            lignes.append(f"**{texte}**")
        else:
            lignes.append(texte)
    return "\n\n".join(lignes)


def _est_ligne_en_gras(paragraphe, texte: str) -> bool:
    """Un court paragraphe entièrement en gras est probablement un titre saisi à la main."""
    if len(texte) > _TITRE_COURT_MAX or not paragraphe.runs:
        return False
    return all(run.bold for run in paragraphe.runs if run.text.strip())


# --- PDF -------------------------------------------------------------------

_TOLERANCE_LIGNE = 3  # écart vertical (en points) en dessous duquel deux mots sont sur la même ligne
_ECART_TAILLE_TITRE = 0.9  # un titre est au moins ~1 pt plus gros que le texte courant


def _extraire_pdf(fichier, max_pages: int, max_caracteres: int) -> str:
    """Lit au plus `max_pages` pages et s'arrête dès que `max_caracteres` sont atteints."""
    import pdfplumber

    lignes = []  # (texte, taille, gras)
    nb_caracteres = 0
    try:
        with pdfplumber.open(fichier) as pdf:
            for page in pdf.pages[:max_pages]:
                mots = page.extract_words(extra_attrs=["size", "fontname"])
                nouvelles = _regrouper_en_lignes(mots)
                lignes.extend(nouvelles)
                nb_caracteres += sum(len(texte) for texte, _, _ in nouvelles)
                if nb_caracteres >= max_caracteres:
                    break
    except Exception as exc:  # PDF corrompu, chiffré, etc.
        raise ExtractionError("Impossible de lire ce fichier PDF : il est corrompu ou protégé.") from exc

    if not lignes:
        return ""
    return _lignes_pdf_vers_markdown(lignes)


def _regrouper_en_lignes(mots):
    lignes, courante, haut = [], [], None
    for mot in mots:
        if courante and abs(mot["top"] - haut) > _TOLERANCE_LIGNE:
            lignes.append(_fusionner_mots(courante))
            courante = []
        if not courante:
            haut = mot["top"]
        courante.append(mot)
    if courante:
        lignes.append(_fusionner_mots(courante))
    return lignes


def _fusionner_mots(mots):
    texte = " ".join(m["text"] for m in mots)
    taille = round(max(m["size"] for m in mots), 1)
    gras = all("bold" in m["fontname"].lower() for m in mots)
    return texte, taille, gras


def _lignes_pdf_vers_markdown(lignes) -> str:
    # Taille « courante » = celle qui porte le plus de caractères.
    poids = Counter()
    for texte, taille, _ in lignes:
        poids[round(taille)] += len(texte)
    taille_courante = poids.most_common(1)[0][0]

    tailles_titres = sorted({t for _, t, _ in lignes if t >= taille_courante + _ECART_TAILLE_TITRE}, reverse=True)
    niveau_par_taille = {t: min(i + 1, 3) for i, t in enumerate(tailles_titres)}

    sortie, niveau_precedent = [], None
    for texte, taille, gras in lignes:
        niveau = niveau_par_taille.get(taille)
        if niveau:
            if niveau == niveau_precedent and sortie:
                sortie[-1] += f" {texte}"  # titre long coupé sur deux lignes
            else:
                sortie.append(f"{'#' * niveau} {texte}")
            niveau_precedent = niveau
            continue
        niveau_precedent = None
        if gras and len(texte) <= _TITRE_COURT_MAX and not texte.endswith((".", ",", ";")):
            sortie.append(f"**{texte}**")
        else:
            sortie.append(texte)
    return "\n".join(sortie)
