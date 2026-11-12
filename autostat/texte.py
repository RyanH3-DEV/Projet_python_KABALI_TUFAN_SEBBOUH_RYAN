"""Helpers for decoding the source data and its French codebook."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

MOTS = (
    "zero", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve",
)
CORRECTIONS = {"alfa-romero": "alfa-romeo", "peugot": "peugeot"}


def analyser_modalites(texte: str) -> dict[str, str]:
    """Parse semicolon-separated ``code:label`` pairs."""
    modalites: dict[str, str] = {}
    for morceau in texte.split(";"):
        morceau = morceau.strip()
        if not morceau:
            continue
        code, separateur, libelle = morceau.partition(":")
        if not separateur:
            raise ValueError(f"Modalité invalide : {morceau!r}")
        modalites[code.strip()] = libelle.strip()
    return modalites


def analyser_ligne_codebook(ligne: str) -> tuple[str, str, dict[str, str]]:
    """Decode one non-comment line from ``codebook.txt``."""
    morceaux = ligne.split("|", 2)
    if len(morceaux) != 3:
        raise ValueError(f"Ligne de codebook invalide : {ligne!r}")
    colonne, libelle, description = (morceau.strip() for morceau in morceaux)
    if not colonne or not libelle:
        raise ValueError(f"Ligne de codebook invalide : {ligne!r}")
    modalites = (
        {} if description.casefold() == "numérique"
        else analyser_modalites(description)
    )
    return colonne, libelle, modalites


def lire_codebook(
    lignes: Iterable[str],
) -> dict[str, tuple[str, dict[str, str]]]:
    """Read the codebook while preserving the column order."""
    codebook: dict[str, tuple[str, dict[str, str]]] = {}
    for ligne in lignes:
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        colonne, libelle, modalites = analyser_ligne_codebook(ligne)
        if colonne in codebook:
            raise ValueError(f"Colonne dupliquée dans le codebook : {colonne}")
        codebook[colonne] = (libelle, modalites)
    return codebook


def mot_en_nombre(mot: str) -> int:
    """Convert an English number word from zero through twelve."""
    try:
        return MOTS.index(mot.strip().casefold())
    except ValueError as exc:
        raise ValueError(f"Nombre en lettres inconnu : {mot!r}") from exc


def corriger_marque(code: str) -> str:
    """Correct the two known source spelling errors without fuzzy matching."""
    valeur = code.strip()
    return CORRECTIONS.get(valeur.casefold(), valeur)


def convertir_valeur(texte: str) -> float | None:
    """Convert a numeric cell, representing the source's ``?`` as None."""
    valeur = texte.strip()
    if valeur == "?":
        return None
    try:
        nombre = float(valeur)
    except ValueError as exc:
        raise ValueError(f"Valeur non numérique : {texte!r}") from exc
    if not math.isfinite(nombre):
        raise ValueError(f"Valeur non numérique : {texte!r}")
    return nombre


def trier_identifiants(identifiants: Iterable[str]) -> list[str]:
    """Sort vehicle IDs naturally (V2 before V10)."""

    def cle(identifiant: str) -> tuple[str, int, int | str]:
        prefixe, suffixe = identifiant[:1].casefold(), identifiant[1:]
        if suffixe.isdigit():
            return prefixe, 0, int(suffixe)
        return prefixe, 1, suffixe.casefold()

    return sorted(identifiants, key=cle)


def fiche_vehicule(
    codebook: Mapping[str, tuple[str, Mapping[str, str]]],
    valeurs: Iterable[object],
) -> str:
    """Format the vehicle fields highlighted in the assignment."""
    associes = dict(zip(codebook, valeurs))
    colonnes = (
        "make", "body-style", "num-of-doors", "num-of-cylinders",
        "normalized-losses", "horsepower", "price",
    )
    lignes: list[str] = []
    for colonne in colonnes:
        if colonne not in codebook or colonne not in associes:
            continue
        libelle, modalites = codebook[colonne]
        valeur = associes[colonne]
        if valeur is None or str(valeur).strip() == "?":
            affichage = "non renseigné"
        elif colonne == "make":
            code = corriger_marque(str(valeur))
            affichage = {
                "alfa-romeo": "Alfa Romeo",
                "peugeot": "Peugeot",
            }.get(code, modalites.get(str(valeur), code.replace("-", " ").title()))
        elif colonne in ("num-of-doors", "num-of-cylinders"):
            affichage = str(mot_en_nombre(str(valeur)))
        else:
            affichage = modalites.get(str(valeur), str(valeur))
        lignes.append(f"{libelle:<29} : {affichage}")
    return "\n".join(lignes)


def histogramme_texte(effectifs: Mapping[str, int], largeur: int) -> str:
    """Render a scaled horizontal histogram using ``#`` characters."""
    if largeur < 0:
        raise ValueError("La largeur doit être positive ou nulle.")
    if not effectifs:
        return ""
    maximum = max(effectifs.values(), default=0)
    longueur_libelle = max(map(len, effectifs))
    lignes = []
    for libelle, effectif in effectifs.items():
        barre = round(effectif / maximum * largeur) if maximum else 0
        lignes.append(f"{libelle:>{longueur_libelle}} | {'#' * barre:<{largeur}} {effectif}")
    return "\n".join(lignes)
