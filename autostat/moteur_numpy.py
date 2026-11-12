"""Vectorized NumPy implementations matching moteur_boucles."""

from __future__ import annotations

import numpy as np


def _vecteur(valeurs) -> np.ndarray:
    tableau = np.asarray(valeurs, dtype=float)
    if tableau.ndim != 1:
        raise ValueError("Une séquence à une dimension est nécessaire.")
    if tableau.size == 0:
        raise ValueError("Une séquence non vide est nécessaire.")
    return tableau


def moyenne(valeurs) -> float:
    return float(np.mean(_vecteur(valeurs)))


def ecart_type(valeurs) -> float:
    return float(np.std(_vecteur(valeurs)))


def moyenne_par_groupe(valeurs, groupes) -> dict[object, float]:
    valeurs_array = _vecteur(valeurs)
    groupes_array = np.asarray(groupes)
    if valeurs_array.size != groupes_array.size:
        raise ValueError("Les valeurs et les groupes doivent avoir la même taille.")
    uniques, inverse = np.unique(groupes_array, return_inverse=True)
    sommes = np.bincount(inverse, weights=valeurs_array)
    effectifs = np.bincount(inverse)
    return dict(zip(uniques.tolist(), (sommes / effectifs).tolist()))


def part_au_dessus(prix, seuil: float = 15000) -> float:
    return float((_vecteur(prix) > seuil).mean())


def correlation(x, y) -> float:
    x_array, y_array = _vecteur(x), _vecteur(y)
    if x_array.size != y_array.size:
        raise ValueError("Les deux séquences doivent avoir la même taille.")
    x_centre, y_centre = x_array - x_array.mean(), y_array - y_array.mean()
    denominateur = np.sqrt((x_centre @ x_centre) * (y_centre @ y_centre))
    return float((x_centre @ y_centre) / denominateur) if denominateur else float("nan")


def correlations_colonnes(X, y) -> np.ndarray:
    X_array = np.asarray(X, dtype=float)
    y_array = _vecteur(y)
    if X_array.ndim != 2 or X_array.shape[0] != y_array.size or not X_array.shape[0]:
        raise ValueError("X doit être une matrice ayant autant de lignes que y.")
    X_centre = X_array - X_array.mean(axis=0)
    y_centre = y_array - y_array.mean()
    denominateurs = np.sqrt((X_centre * X_centre).sum(axis=0) * (y_centre @ y_centre))
    return np.divide(
        y_centre @ X_centre,
        denominateurs,
        out=np.full(X_array.shape[1], np.nan),
        where=denominateurs != 0,
    )
