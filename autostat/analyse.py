"""Analysis shared by both computation engines."""

from __future__ import annotations

import math
import timeit
from collections.abc import Sequence

import numpy as np

from . import moteur_boucles, moteur_numpy
from .structures import MATRICE_COLONNES

MOTEURS = {"boucles": moteur_boucles, "numpy": moteur_numpy}


def lignes_completes(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    X_array = np.asarray(X, dtype=float)
    y_array = np.asarray(y, dtype=float)
    if X_array.ndim != 2 or y_array.ndim != 1 or X_array.shape[0] != y_array.size:
        raise ValueError("X doit être une matrice et y un vecteur de même longueur.")
    masque = ~np.isnan(X_array).any(axis=1) & ~np.isnan(y_array)
    return X_array[masque], y_array[masque]


def synthese(
    moteur,
    X: np.ndarray,
    y: np.ndarray,
    groupes: Sequence[object] | None = None,
    libelles: Sequence[str] = MATRICE_COLONNES,
) -> dict[str, float | str]:
    X_array = np.asarray(X, dtype=float)
    y_array = np.asarray(y, dtype=float)
    masque = ~np.isnan(X_array).any(axis=1) & ~np.isnan(y_array)
    X_propre, y_propre = X_array[masque], y_array[masque]
    if not y_propre.size:
        raise ValueError("Aucune ligne complète à analyser.")
    correlations = moteur.correlations_colonnes(X_propre, y_propre)
    corr_array = np.asarray(correlations, dtype=float)
    indices_valides = np.flatnonzero(~np.isnan(corr_array))
    if not indices_valides.size:
        raise ValueError("Aucune corrélation calculable.")
    indice = int(indices_valides[np.argmax(np.abs(corr_array[indices_valides]))])
    resultat: dict[str, float | str] = {
        "prix_moyen": moteur.moyenne(y_propre),
        "ecart_type_prix": moteur.ecart_type(y_propre),
        "part_plus_15000": moteur.part_au_dessus(y_propre),
        "variable_plus_correlee": libelles[indice],
        "correlation": moteur.correlation(X_propre[:, indice], y_propre),
    }
    if groupes is not None:
        groupes_array = np.asarray(groupes)
        if groupes_array.size != masque.size:
            raise ValueError("Le vecteur de groupes doit correspondre aux lignes de X.")
        groupes_propres = groupes_array[masque]
        moyennes = moteur.moyenne_par_groupe(y_propre, groupes_propres)
        if "turbo" in moyennes:
            resultat["prix_moyen_turbo"] = moyennes["turbo"]
    return resultat


def facteurs_principaux(
    X: np.ndarray,
    y: np.ndarray,
    libelles: Sequence[str],
    k: int = 6,
) -> list[tuple[str, float]]:
    X_propre, y_propre = lignes_completes(X, y)
    correlations = np.asarray(
        moteur_numpy.correlations_colonnes(X_propre, y_propre), dtype=float
    )
    ordre = np.argsort(np.nan_to_num(np.abs(correlations), nan=-1.0))[::-1][:k]
    return [(libelles[int(i)], float(correlations[i])) for i in ordre]


def chronometrer(X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    X_propre, y_propre = lignes_completes(X, y)
    repetitions = max(1, math.ceil(100_000 / len(y_propre)))
    X_large = np.tile(X_propre, (repetitions, 1))[:100_000]
    y_large = np.tile(y_propre, repetitions)[:100_000]
    durees = {
        nom: timeit.timeit(
            lambda moteur=moteur: moteur.correlations_colonnes(X_large, y_large),
            number=1,
        )
        for nom, moteur in MOTEURS.items()
    }
    durees["acceleration"] = durees["boucles"] / durees["numpy"]
    durees["lignes"] = float(len(y_large))
    return durees
