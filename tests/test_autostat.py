from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np

from autostat import analyse, moteur_boucles, moteur_numpy
from autostat.chargement import (
    bilan,
    charger_codebook,
    charger_vehicules,
    convertir_ligne,
    exporter_json,
    exporter_lisible,
    ouvrir_texte,
)
from autostat.exceptions import FichierDonneesErreur, LigneInvalideErreur
from autostat.structures import (
    MATRICE_COLONNES,
    apercu_numpy,
    tableau_croise,
    depuis_lignes,
    repartition_carburants,
    vers_matrice,
)
from autostat.texte import (
    analyser_modalites,
    corriger_marque,
    lire_codebook,
    mot_en_nombre,
    trier_identifiants,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "donnees"


class TexteTests(unittest.TestCase):
    def test_modalites_codebook_et_conversions(self) -> None:
        self.assertEqual(
            analyser_modalites("-1:Plutôt sûr ; 0:Neutre"),
            {"-1": "Plutôt sûr", "0": "Neutre"},
        )
        with self.assertRaises(ValueError):
            analyser_modalites("modalité invalide")
        codebook = lire_codebook((DATA / "codebook.txt").read_text(encoding="utf-8").splitlines())
        self.assertEqual(len(codebook), 26)
        self.assertEqual(mot_en_nombre("twelve"), 12)
        self.assertEqual(corriger_marque("peugot"), "peugeot")
        self.assertEqual(trier_identifiants(["V10", "V2"]), ["V2", "V10"])


class StructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.codebook = charger_codebook(DATA / "codebook.txt")
        cls.vehicules, cls.rapport = charger_vehicules(
            DATA / "automobile.zip", cls.codebook
        )

    def test_tableaux_et_repartition(self) -> None:
        X, y = vers_matrice(self.vehicules)
        resume = apercu_numpy(X, y)
        self.assertEqual(X.shape, (205, 17))
        self.assertEqual(X.shape[1], len(MATRICE_COLONNES))
        self.assertEqual(self.rapport["valides"], 205)
        self.assertEqual(repartition_carburants(self.vehicules), (
            {"Essence": 185, "Diesel": 20}, 4
        ))
        croise = tableau_croise(self.vehicules, "drive-wheels", self.codebook)
        self.assertEqual(
            [croise[code]["effectif"] for code in ("4wd", "fwd", "rwd")],
            [8, 118, 75],
        )
        self.assertEqual(resume["lignes_completes"], 159)
        self.assertEqual(resume["nan_par_colonne"][1], 41)

    def test_raw_rows_create_numbered_records(self) -> None:
        lignes = [
            "3,?,alfa-romero,gas,std,two,convertible,rwd,front,88.60,168.80,64.10,48.80,2548,dohc,four,130,mpfi,3.47,2.68,9.00,111,5000,21,27,13495"
        ]
        vehicule = depuis_lignes(lignes, list(self.codebook))[0]
        self.assertEqual(vehicule.identifiant, "V1")
        self.assertEqual(vehicule.numero, 1)
        self.assertEqual(vehicule.marque, "alfa-romeo")
        self.assertEqual(vehicule.prix, 13495.0)
        self.assertFalse(vehicule.complet)
        complete = depuis_lignes(
            [lignes[0].replace("3,?,", "3,100,", 1)], list(self.codebook)
        )[0]
        self.assertTrue(complete.complet)


class AnalyseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        codebook = charger_codebook(DATA / "codebook.txt")
        cls.vehicules, _ = charger_vehicules(DATA / "automobile.zip", codebook)
        cls.X, cls.y = vers_matrice(cls.vehicules)

    def test_boucles_et_numpy_sont_equivalents(self) -> None:
        X, y = analyse.lignes_completes(self.X, self.y)
        np.testing.assert_allclose(
            moteur_boucles.correlations_colonnes(X, y),
            moteur_numpy.correlations_colonnes(X, y),
            atol=1e-12,
        )
        resultats = [
            analyse.synthese(moteur, self.X, self.y)
            for moteur in (moteur_boucles, moteur_numpy)
        ]
        for cle in ("prix_moyen", "ecart_type_prix", "part_plus_15000", "correlation"):
            self.assertAlmostEqual(resultats[0][cle], resultats[1][cle], places=9)
        self.assertEqual(resultats[0]["variable_plus_correlee"], "curb-weight")


class ChargementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.codebook = charger_codebook(DATA / "codebook.txt")

    def test_zip_et_fichier_extrait_contiennent_les_memes_vehicules(self) -> None:
        depuis_zip, rapport_zip = charger_vehicules(DATA / "automobile.zip", self.codebook)
        depuis_fichier, rapport_fichier = charger_vehicules(
            DATA / "imports-85.data", self.codebook
        )
        self.assertEqual(depuis_zip, depuis_fichier)
        self.assertEqual(rapport_zip, rapport_fichier)

    def test_echantillon_corrompu_rejette_sans_arreter(self) -> None:
        vehicules, rapport = charger_vehicules(
            DATA / "echantillon_corrompu.data", self.codebook
        )
        self.assertEqual(len(vehicules), 2)
        self.assertEqual(rapport["rejets"], 6)
        self.assertEqual(rapport["valides"], 2)

    def test_ligne_invalide_et_archive_corrompue(self) -> None:
        ligne = [""] * 25
        with self.assertRaises(LigneInvalideErreur):
            convertir_ligne(ligne, 12, self.codebook)
        with tempfile.TemporaryDirectory() as temporaire:
            fichier = Path(temporaire) / "casse.zip"
            fichier.write_bytes(b"not a zip file")
            with self.assertRaises(FichierDonneesErreur):
                ouvrir_texte(fichier)

    def test_bilan_et_exports(self) -> None:
        vehicules, rapport = charger_vehicules(DATA / "automobile.zip", self.codebook)
        resume = bilan(vehicules, self.codebook)
        self.assertEqual(resume["effectif"], 205)
        self.assertAlmostEqual(resume["prix_moyen"], 13207.1, places=1)
        self.assertEqual(resume["quartiles_prix"], [7775.0, 10295.0, 16501.5])
        with tempfile.TemporaryDirectory() as temporaire:
            csv_path = exporter_lisible(
                vehicules, self.codebook, Path(temporaire) / "lisible.csv"
            )
            json_path = exporter_json(
                rapport, Path(temporaire) / "rapport.json", resume
            )
            self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertIn("Empattement (cm)", csv_path.read_text(encoding="utf-8-sig"))
            self.assertIn("225.04", csv_path.read_text(encoding="utf-8-sig"))
            contenu = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("genere_le", contenu)
            self.assertEqual(contenu["qualite"]["valides"], 205)


if __name__ == "__main__":
    unittest.main()
