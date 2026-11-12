"""Validated file and archive loading, summaries, and export functions."""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import fmean, median_low, mode, pstdev, quantiles
from typing import Mapping, Sequence

from .exceptions import FichierDonneesErreur, LigneInvalideErreur
from .structures import Vehicule
from .texte import corriger_marque, mot_en_nombre

LOGGER = logging.getLogger(__name__)


class _ArchiveTextStream(io.TextIOWrapper):
    def __init__(self, flux, archive: zipfile.ZipFile) -> None:
        self._archive = archive
        super().__init__(flux, encoding="utf-8-sig", newline="")

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._archive.close()


def charger_codebook(
    chemin: str | Path,
) -> dict[str, tuple[str, dict[str, str]]]:
    from .texte import lire_codebook

    path = Path(chemin)
    try:
        with path.open(encoding="utf-8-sig") as fichier:
            return lire_codebook(fichier)
    except FileNotFoundError as exc:
        raise FichierDonneesErreur(f"Fichier introuvable : {path}") from exc
    except (OSError, ValueError) as exc:
        raise FichierDonneesErreur(f"Codebook illisible : {path} ({exc})") from exc


def ouvrir_texte(chemin: str | Path):
    """Open a text file or the ``imports-85.data`` member of a ZIP archive."""
    path = Path(chemin)
    try:
        if path.suffix.casefold() != ".zip":
            return path.open(encoding="utf-8-sig", newline="")
        archive = zipfile.ZipFile(path)
        membre = next(
            (
                nom for nom in archive.namelist()
                if nom.replace("\\", "/").endswith("imports-85.data")
            ),
            None,
        )
        if membre is None:
            archive.close()
            raise FichierDonneesErreur(
                f"Aucun membre imports-85.data dans l'archive : {path}"
            )
        try:
            return _ArchiveTextStream(archive.open(membre), archive)
        except (KeyError, OSError, RuntimeError, ValueError):
            archive.close()
            raise
    except FileNotFoundError as exc:
        raise FichierDonneesErreur(f"Fichier introuvable : {path}") from exc
    except zipfile.BadZipFile as exc:
        raise FichierDonneesErreur(f"Archive ZIP invalide : {path}") from exc
    except OSError as exc:
        raise FichierDonneesErreur(f"Impossible de lire : {path} ({exc})") from exc


def convertir_ligne(
    valeurs: Sequence[str],
    numero: int,
    codebook: Mapping[str, tuple[str, Mapping[str, str]]],
) -> Vehicule:
    colonnes = list(codebook)
    if len(valeurs) != len(colonnes):
        raise LigneInvalideErreur(
            numero, f"nombre de colonnes incorrect ({len(valeurs)} au lieu de {len(colonnes)})"
        )
    attributs: dict[str, object | None] = {}
    for colonne, valeur_brute in zip(colonnes, valeurs):
        valeur = valeur_brute.strip()
        if valeur == "?":
            attributs[colonne] = None
            continue
        modalites = codebook[colonne][1]
        if modalites and valeur not in modalites:
            raise LigneInvalideErreur(
                numero, f"code hors dictionnaire (colonne {colonne} : {valeur!r})"
            )
        if colonne == "num-of-doors" or colonne == "num-of-cylinders":
            try:
                attributs[colonne] = float(mot_en_nombre(valeur))
            except ValueError as exc:
                raise LigneInvalideErreur(
                    numero, f"code hors dictionnaire (colonne {colonne} : {valeur!r})"
                ) from exc
        elif colonne == "make":
            attributs[colonne] = corriger_marque(valeur)
        elif colonne == "symboling":
            attributs[colonne] = float(valeur)
        elif not modalites:
            try:
                nombre = float(valeur)
            except ValueError as exc:
                raise LigneInvalideErreur(
                    numero, f"valeur non numérique (colonne {colonne} : {valeur!r})"
                ) from exc
            if not math.isfinite(nombre):
                raise LigneInvalideErreur(
                    numero, f"valeur non numérique (colonne {colonne} : {valeur!r})"
                )
            if colonne == "price" and nombre < 0:
                raise LigneInvalideErreur(numero, "valeur négative (colonne price)")
            attributs[colonne] = nombre
        else:
            attributs[colonne] = valeur
    prix = attributs.get("price")
    return Vehicule(f"V{numero}", attributs, prix if isinstance(prix, float) else None)


def charger_vehicules(
    chemin: str | Path,
    codebook: Mapping[str, tuple[str, Mapping[str, str]]],
) -> tuple[list[Vehicule], dict[str, object]]:
    vehicules: list[Vehicule] = []
    motifs: Counter[str] = Counter()
    manquants: Counter[str] = Counter()
    lignes_vues: dict[tuple[str, ...], int] = {}
    rejets = 0
    flux = ouvrir_texte(chemin)
    try:
        lecteur = csv.reader(flux)
        for numero, valeurs in enumerate(lecteur, start=1):
            if not valeurs or (len(valeurs) == 1 and not valeurs[0].strip()):
                continue
            try:
                vehicule = convertir_ligne(valeurs, numero, codebook)
                cle = tuple(valeur.strip() for valeur in valeurs)
                if cle in lignes_vues:
                    raise LigneInvalideErreur(
                        numero, f"doublon (ligne {lignes_vues[cle]})"
                    )
                lignes_vues[cle] = numero
            except LigneInvalideErreur as exc:
                rejets += 1
                motifs[exc.motif] += 1
                LOGGER.warning("Rejet ligne %s : %s", numero, exc.motif)
                continue
            vehicules.append(vehicule)
            for colonne, valeur in vehicule.attributs.items():
                if valeur is None:
                    manquants[colonne] += 1
    finally:
        flux.close()
    rapport = {
        "valides": len(vehicules),
        "rejets": rejets,
        "motifs": dict(motifs),
        "manquants": dict(manquants),
    }
    return vehicules, rapport


def bilan(
    vehicules: Sequence[Vehicule],
    codebook: Mapping[str, tuple[str, Mapping[str, str]]],
) -> dict[str, object]:
    prix = [vehicule.prix for vehicule in vehicules if vehicule.prix is not None]
    if not prix:
        raise FichierDonneesErreur("Aucun prix valide pour établir le bilan.")
    marques = [
        vehicule.marque for vehicule in vehicules if vehicule.marque is not None
    ]
    marque_frequente = mode(marques)
    noms = {
        "alfa-romeo": "Alfa Romeo",
        "peugeot": "Peugeot",
        "bmw": "BMW",
        "mercedes-benz": "Mercedes-Benz",
    }
    quartiles = quantiles(prix, n=4)
    return {
        "effectif": len(vehicules),
        "prix_moyen": fmean(prix),
        "prix_median": median_low(prix),
        "marque_la_plus_frequente": noms.get(
            marque_frequente, marque_frequente.title()
        ),
        "ecart_type_prix": pstdev(prix),
        "quartiles_prix": quartiles,
    }


def _format_nombre(valeur: float, decimales: int = 2) -> str:
    if float(valeur).is_integer():
        return str(int(valeur))
    return f"{valeur:.{decimales}f}"


def _valeur_lisible(colonne: str, valeur: object | None, modalites) -> str:
    if valeur is None:
        return ""
    if colonne == "make":
        code = corriger_marque(str(valeur))
        return {
            "alfa-romeo": "Alfa Romeo",
            "peugeot": "Peugeot",
            "bmw": "BMW",
            "mercedes-benz": "Mercedes-Benz",
        }.get(code, code.title())
    if colonne == "num-of-doors" or colonne == "num-of-cylinders":
        try:
            return str(mot_en_nombre(str(valeur)))
        except ValueError:
            return _format_nombre(float(valeur))
    if modalites and str(valeur) in modalites:
        return modalites[str(valeur)]
    return _format_nombre(valeur) if isinstance(valeur, (int, float)) else str(valeur)


def _conversion_unite(colonne: str, valeur: object | None) -> float | None:
    if valeur is None:
        return None
    nombre = float(valeur)
    if colonne in ("wheel-base", "length", "width", "height", "bore", "stroke"):
        return nombre * 2.54
    if colonne == "curb-weight":
        return nombre * 0.45359237
    if colonne in ("city-mpg", "highway-mpg"):
        return 235.21 / nombre
    return nombre


def exporter_lisible(
    vehicules: Sequence[Vehicule],
    codebook: Mapping[str, tuple[str, Mapping[str, str]]],
    chemin: str | Path,
) -> Path:
    path = Path(chemin)
    path.parent.mkdir(parents=True, exist_ok=True)
    noms_colonnes = {
        "wheel-base": "Empattement (cm)",
        "length": "Longueur (cm)",
        "width": "Largeur (cm)",
        "height": "Hauteur (cm)",
        "bore": "Alésage (cm)",
        "stroke": "Course (cm)",
        "curb-weight": "Poids à vide (kg)",
        "city-mpg": "Consommation en ville (l/100 km)",
        "highway-mpg": "Consommation sur route (l/100 km)",
    }
    champs = ["Identifiant"] + [
        noms_colonnes.get(colonne, codebook[colonne][0])
        for colonne in codebook
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")
        writer.writeheader()
        for vehicule in vehicules:
            ligne: dict[str, str] = {"Identifiant": vehicule.identifiant}
            for colonne, (libelle, modalites) in codebook.items():
                valeur = vehicule.attribut(colonne)
                champ = noms_colonnes.get(colonne, libelle)
                if colonne in noms_colonnes:
                    convertie = _conversion_unite(colonne, valeur)
                    ligne[champ] = "" if convertie is None else _format_nombre(convertie)
                else:
                    ligne[champ] = _valeur_lisible(colonne, valeur, modalites)
            writer.writerow(ligne)
    return path


def exporter_json(
    rapport: Mapping[str, object],
    chemin: str | Path,
    resume: Mapping[str, object] | None = None,
) -> Path:
    path = Path(chemin)
    path.parent.mkdir(parents=True, exist_ok=True)
    contenu = {
        "genere_le": datetime.now().astimezone().isoformat(timespec="seconds"),
        "qualite": dict(rapport),
    }
    if resume is not None:
        contenu["bilan"] = dict(resume)
    with path.open("w", encoding="utf-8") as fichier:
        json.dump(contenu, fichier, ensure_ascii=False, indent=2)
        fichier.write("\n")
    return path
