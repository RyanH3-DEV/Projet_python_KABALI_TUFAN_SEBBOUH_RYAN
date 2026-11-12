"""Typed vehicle records and NumPy representations."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import fmean
from typing import Iterable, Mapping, Sequence

import numpy as np

from .texte import convertir_valeur, corriger_marque, mot_en_nombre

MATRICE_COLONNES = (
    "symboling", "normalized-losses", "num-of-doors", "wheel-base",
    "length", "width", "height", "curb-weight", "num-of-cylinders",
    "engine-size", "bore", "stroke", "compression-ratio", "horsepower",
    "peak-rpm", "city-mpg", "highway-mpg",
)


@dataclass(frozen=True)
class Vehicule:
    identifiant: str
    attributs: Mapping[str, object]
    prix: float | None
    numero: int = field(init=False)

    def __post_init__(self) -> None:
        suffixe = self.identifiant[1:] if self.identifiant.startswith("V") else ""
        if not suffixe.isdigit():
            raise ValueError(f"Identifiant de véhicule invalide : {self.identifiant!r}")
        object.__setattr__(self, "numero", int(suffixe))

    def attribut(self, nom: str) -> object | None:
        return self.attributs.get(nom)

    @property
    def marque(self) -> str | None:
        valeur = self.attribut("make")
        return corriger_marque(str(valeur)) if valeur is not None else None

    @property
    def complet(self) -> bool:
        return self.prix is not None and all(
            valeur is not None for valeur in self.attributs.values()
        )


def _convertir_attribut(colonne: str, valeur: str) -> object | None:
    valeur = valeur.strip()
    if valeur == "?":
        return None
    if colonne in ("num-of-doors", "num-of-cylinders"):
        return float(mot_en_nombre(valeur))
    if colonne == "symboling" or valeur.replace(".", "", 1).replace("-", "", 1).isdigit():
        return convertir_valeur(valeur)
    return valeur


def depuis_lignes(
    lignes: Iterable[Sequence[str] | str],
    colonnes: Sequence[str],
) -> list[Vehicule]:
    """Build vehicles from raw CSV rows, assigning stable V1... IDs."""
    vehicules = []
    for numero, ligne in enumerate(lignes, start=1):
        valeurs = next(csv.reader([ligne])) if isinstance(ligne, str) else list(ligne)
        if len(valeurs) != len(colonnes):
            raise ValueError(
                f"Ligne {numero} : {len(valeurs)} colonnes au lieu de {len(colonnes)}"
            )
        attributs = {
            colonne: _convertir_attribut(colonne, valeur)
            for colonne, valeur in zip(colonnes, valeurs)
        }
        prix = attributs.get("price")
        vehicules.append(
            Vehicule(f"V{numero}", attributs, prix if isinstance(prix, float) else None)
        )
    return vehicules


def repartition_carburants(
    vehicules: Iterable[Vehicule],
) -> tuple[dict[str, int], int]:
    effectifs: Counter[str] = Counter()
    prix_manquants = 0
    for vehicule in vehicules:
        carburant = vehicule.attribut("fuel-type")
        if carburant is not None:
            libelle = {"gas": "Essence", "diesel": "Diesel"}.get(
                str(carburant), str(carburant)
            )
            effectifs[libelle] += 1
        prix_manquants += vehicule.prix is None
    ordre = ("Essence", "Diesel")
    return ({nom: effectifs[nom] for nom in ordre if nom in effectifs}, prix_manquants)


def index_par_marque(
    vehicules: Iterable[Vehicule],
) -> dict[str, dict[str, list[str]]]:
    index: defaultdict[str, defaultdict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for vehicule in vehicules:
        if vehicule.marque is not None:
            valeur_carburant = vehicule.attribut("fuel-type")
            if valeur_carburant is None:
                continue
            carburant = str(valeur_carburant)
            index[vehicule.marque][carburant].append(vehicule.identifiant)
    return {marque: dict(carburants) for marque, carburants in index.items()}


def tableau_croise(
    vehicules: Iterable[Vehicule],
    colonne: str,
    codebook: Mapping[str, tuple[str, Mapping[str, str]]],
) -> dict[str, dict[str, float | int | None]]:
    groupes: defaultdict[str, list[float]] = defaultdict(list)
    comptes: Counter[str] = Counter()
    for vehicule in vehicules:
        valeur = vehicule.attribut(colonne)
        if valeur is None:
            continue
        code = str(valeur)
        groupes[code]
        if vehicule.prix is not None:
            comptes[code] += 1
            groupes[code].append(vehicule.prix)
    modalites = codebook.get(colonne, ("", {}))[1]
    codes = list(modalites) if modalites else sorted(comptes)
    return {
        code: {
            "effectif": comptes[code],
            "prix_moyen": fmean(groupes[code]) if groupes[code] else None,
        }
        for code in codes
    }


def _nom_marque(code: str) -> str:
    noms = {
        "alfa-romeo": "Alfa Romeo",
        "peugeot": "Peugeot",
        "bmw": "BMW",
        "mercedes-benz": "Mercedes-Benz",
    }
    return noms.get(code, code.title())


def classement_marques(
    vehicules: Iterable[Vehicule],
    effectif_min: int = 8,
) -> list[tuple[str, int, float]]:
    prix_par_marque: defaultdict[str, list[float]] = defaultdict(list)
    for vehicule in vehicules:
        if vehicule.marque is not None and vehicule.prix is not None:
            prix_par_marque[vehicule.marque].append(vehicule.prix)
    resultats = [
        (_nom_marque(marque), len(prix), fmean(prix))
        for marque, prix in prix_par_marque.items()
        if len(prix) >= effectif_min
    ]
    return sorted(resultats, key=lambda ligne: (-ligne[2], ligne[0].casefold()))


def _nombre_matrice(vehicule: Vehicule, colonne: str) -> float:
    valeur = vehicule.attribut(colonne)
    if valeur is None:
        return math.nan
    if colonne in ("num-of-doors", "num-of-cylinders") and isinstance(valeur, str):
        return float(mot_en_nombre(valeur))
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return math.nan


def vers_matrice(
    vehicules: Iterable[Vehicule],
) -> tuple[np.ndarray, np.ndarray]:
    lignes = list(vehicules)
    X = np.asarray(
        [[_nombre_matrice(vehicule, nom) for nom in MATRICE_COLONNES] for vehicule in lignes],
        dtype=float,
    )
    y = np.asarray(
        [np.nan if vehicule.prix is None else vehicule.prix for vehicule in lignes],
        dtype=float,
    )
    return X, y


def apercu_numpy(X: np.ndarray, y: np.ndarray) -> dict[str, object]:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    cylindres = X[:, 8]
    connus = cylindres[~np.isnan(cylindres)].astype(int)
    lignes_completes = (~np.isnan(X).any(axis=1)) & (~np.isnan(y))
    return {
        "forme_X": X.shape,
        "dtype": str(X.dtype),
        "nan_par_colonne": np.isnan(X).sum(axis=0).astype(int).tolist(),
        "lignes_completes": int(lignes_completes.sum()),
        "prix_moyen": float(np.nanmean(y)),
        "cylindres": np.bincount(connus).tolist() if connus.size else [],
    }
