"""Command-line entry point for the four AutoStat project phases."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from autostat import analyse
from autostat.chargement import (
    bilan,
    charger_codebook,
    charger_vehicules,
    exporter_json,
    exporter_lisible,
    ouvrir_texte,
)
from autostat.exceptions import AutoStatErreur
from autostat.structures import (
    MATRICE_COLONNES,
    apercu_numpy,
    classement_marques,
    depuis_lignes,
    index_par_marque,
    repartition_carburants,
    tableau_croise,
    vers_matrice,
)
from autostat.texte import (
    corriger_marque,
    fiche_vehicule,
    histogramme_texte,
    lire_codebook,
    mot_en_nombre,
    trier_identifiants,
)

RACINE = Path(__file__).resolve().parent
CODEBOOK = RACINE / "donnees" / "codebook.txt"
DONNEES = RACINE / "donnees" / "automobile.zip"


def _charger_lignes(chemin: Path) -> list[list[str]]:
    import csv

    with ouvrir_texte(chemin) as flux:
        return [ligne for ligne in csv.reader(flux) if ligne]


def _codebook(chemin: Path):
    with chemin.open(encoding="utf-8-sig") as fichier:
        return lire_codebook(fichier)


def phase1(chemin: Path) -> None:
    codebook = _codebook(CODEBOOK)
    lignes = _charger_lignes(chemin)
    print(f"{len(codebook)} variables décrites, {len(lignes)} véhicules")
    print("===================== Fiche V1 =====================")
    print(fiche_vehicule(codebook, lignes[0]))
    print(
        f"mot_en_nombre('twelve') = {mot_en_nombre('twelve')} ; "
        f"corriger_marque('peugot') = {corriger_marque('peugot')!r}"
    )
    identifiants = [f"V{i}" for i in (1, 10, 100, 101)]
    print(f"Tri alphabétique : {sorted(identifiants)}")
    print(f"Tri naturel      : {trier_identifiants(['V4', 'V1', 'V3', 'V2'])}")
    effectifs: dict[str, int] = {}
    modalites = codebook["body-style"][1]
    indice_carrosserie = list(codebook).index("body-style")
    for ligne in lignes:
        code = ligne[indice_carrosserie]
        effectifs[code] = effectifs.get(code, 0) + 1
    traduits = {
        modalites[code]: effectifs[code]
        for code in modalites
        if code in effectifs
    }
    print("Véhicules par carrosserie :")
    print(histogramme_texte(traduits, 30))


def phase2(chemin: Path) -> None:
    codebook = _codebook(CODEBOOK)
    vehicules = depuis_lignes(_charger_lignes(chemin), list(codebook))
    repartition, prix_manquants = repartition_carburants(vehicules)
    print(f"Répartition : {repartition}")
    print(f"Prix non renseigné : {prix_manquants}")
    index = index_par_marque(vehicules)
    peugeot = index.get("peugeot", {}).get("diesel", [])
    print(f"Peugeot, diesel : {trier_identifiants(peugeot)}")
    croise = tableau_croise(vehicules, "drive-wheels", codebook)
    print("Roues motrices (prix connus) :")
    for code, stats in croise.items():
        libelle = codebook["drive-wheels"][1][code]
        prix = stats["prix_moyen"]
        moyenne = "n/a" if prix is None else f"{prix:8.0f} $"
        print(f"  {libelle:<13} : {stats['effectif']:3} véhicules, prix moyen {moyenne}")
    print("Classement des marques par prix moyen (effectif >= 8) :")
    for rang, (marque, effectif, prix_moyen) in enumerate(
        classement_marques(vehicules), start=1
    ):
        print(f"  {rang:2}. {marque:<15} ({effectif:2} véhicules) : {prix_moyen:7.0f} $")
    X, y = vers_matrice(vehicules)
    print(f"NumPy : {apercu_numpy(X, y)}")


def phase3(chemin: Path) -> None:
    codebook = _codebook(CODEBOOK)
    vehicules = depuis_lignes(_charger_lignes(chemin), list(codebook))
    X, y = vers_matrice(vehicules)
    groupes = [vehicule.attribut("aspiration") for vehicule in vehicules]
    for nom, moteur in analyse.MOTEURS.items():
        print(f"{nom:<8} {analyse.synthese(moteur, X, y, groupes)}")
    complets_X, complets_y = analyse.lignes_completes(X, y)
    print(f"Variables les plus liées au prix ({len(complets_y)} véhicules complets) :")
    for nom, correlation in analyse.facteurs_principaux(X, y, MATRICE_COLONNES):
        print(f"  {nom:<14} {codebook[nom][0]:<30} r = {correlation:+.3f}")
    chronos = analyse.chronometrer(complets_X, complets_y)
    print(
        f"17 corrélations sur {int(chronos['lignes'])} lignes : "
        f"boucles {chronos['boucles']:.3f} s | NumPy {chronos['numpy']:.4f} s | "
        f"accélération x{chronos['acceleration']:.0f}"
    )


def phase4(chemin: Path, verbose: bool) -> None:
    codebook = charger_codebook(CODEBOOK)
    vehicules, rapport = charger_vehicules(chemin, codebook)
    resume = bilan(vehicules, codebook)
    qualite = {cle: rapport[cle] for cle in ("valides", "rejets", "motifs")}
    manquants = rapport["manquants"]
    print(f"Qualité : {qualite}")
    print(f"Manquants : {manquants}")
    print(f"Bilan : {resume}")
    if chemin.resolve() == DONNEES.resolve():
        csv_path = exporter_lisible(
            vehicules, codebook, RACINE / "sorties" / "vehicules_decodes.csv"
        )
        json_path = exporter_json(
            rapport, RACINE / "sorties" / "rapport.json", resume
        )
        print(f"Exports : {csv_path.relative_to(RACINE)} | {json_path.relative_to(RACINE)}")
    elif verbose:
        print("Exports ignorés pour le fichier d'échantillon.")


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        description="Analyse descriptive du catalogue automobile UCI."
    )
    parseur.add_argument("phase", choices=("phase1", "phase2", "phase3", "phase4"))
    parseur.add_argument("--fichier", type=Path, default=DONNEES)
    parseur.add_argument("-v", "--verbose", action="store_true")
    return parseur


def main(argv: list[str] | None = None) -> int:
    args = construire_parseur().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.verbose else logging.ERROR,
        format="%(levelname)s %(name)s : %(message)s",
    )
    try:
        if args.phase == "phase4":
            phase4(args.fichier, args.verbose)
        else:
            globals()[args.phase](args.fichier)
    except AutoStatErreur as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
