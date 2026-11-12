"""Reference implementations using ordinary Python loops."""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Sequence


def _valider_non_vide(valeurs: Sequence[float]) -> None:
    if len(valeurs) == 0:
        raise ValueError("Une séquence non vide est nécessaire.")


def moyenne(valeurs: Sequence[float]) -> float:
    _valider_non_vide(valeurs)
    return sum(float(valeur) for valeur in valeurs) / len(valeurs)


def ecart_type(valeurs: Sequence[float]) -> float:
    _valider_non_vide(valeurs)
    centre = moyenne(valeurs)
    return sqrt(sum((float(valeur) - centre) ** 2 for valeur in valeurs) / len(valeurs))


def moyenne_par_groupe(
    valeurs: Sequence[float],
    groupes: Sequence[object],
) -> dict[object, float]:
    if len(valeurs) != len(groupes):
        raise ValueError("Les valeurs et les groupes doivent avoir la même taille.")
    sommes: defaultdict[object, float] = defaultdict(float)
    effectifs: defaultdict[object, int] = defaultdict(int)
    for valeur, groupe in zip(valeurs, groupes):
        sommes[groupe] += float(valeur)
        effectifs[groupe] += 1
    return {groupe: somme / effectifs[groupe] for groupe, somme in sommes.items()}


def part_au_dessus(prix: Sequence[float], seuil: float = 15000) -> float:
    _valider_non_vide(prix)
    return sum(float(valeur) > seuil for valeur in prix) / len(prix)


def correlation(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) == 0:
        raise ValueError("Les deux séquences doivent avoir la même taille non nulle.")
    moyenne_x, moyenne_y = moyenne(x), moyenne(y)
    centres_x = [float(valeur) - moyenne_x for valeur in x]
    centres_y = [float(valeur) - moyenne_y for valeur in y]
    somme_x = sum(valeur * valeur for valeur in centres_x)
    somme_y = sum(valeur * valeur for valeur in centres_y)
    if somme_x == 0 or somme_y == 0:
        return float("nan")
    return sum(a * b for a, b in zip(centres_x, centres_y)) / sqrt(somme_x * somme_y)


def correlations_colonnes(X, y) -> list[float]:
    if len(X) != len(y) or len(X) == 0:
        raise ValueError("X et y doivent avoir le même nombre de lignes non nul.")
    return [correlation([ligne[j] for ligne in X], y) for j in range(len(X[0]))]
