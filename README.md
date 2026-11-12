# AutoStat

AutoStat est une application Python en ligne de commande pour valider et analyser
les 205 véhicules du jeu de données Automobile de l'UCI. Le projet couvre les
quatre phases de la consigne : traitement du codebook, structures et NumPy,
comparaison de moteurs de calcul, puis chargement robuste et exports.

## Installation

Python 3.10 ou supérieur est requis. Seule dépendance externe : NumPy.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Utilisation

À la racine du projet :

```powershell
python main.py phase1
python main.py phase2
python main.py phase3
python main.py phase4
python main.py phase4 --fichier donnees\echantillon_corrompu.data -v
python -m unittest -v
```

`--fichier` accepte un fichier CSV sans en-tête ou une archive ZIP contenant
`imports-85.data`. La phase 4 génère `sorties/vehicules_decodes.csv` et
`sorties/rapport.json` pour le jeu de données réel.

Le guide détaillé des commandes et résultats attendus est dans
[GUIDE_TESTS.md](./GUIDE_TESTS.md).

## Architecture

- `autostat/texte.py` : décodage du codebook et fonctions textuelles.
- `autostat/structures.py` : objets véhicule, index, tableaux et conversion NumPy.
- `autostat/moteur_boucles.py` et `autostat/moteur_numpy.py` : interfaces de calcul
  équivalentes, respectivement de référence et vectorisée.
- `autostat/analyse.py` : nettoyage, synthèse, corrélations et chronométrage.
- `autostat/chargement.py` : lecture du ZIP sans extraction, validation, bilan et exports.
- `autostat/exceptions.py` : erreurs applicatives explicites.

Les valeurs manquantes `?` ne sont pas des rejets. Les lignes invalides et les
doublons sont comptabilisés et ignorés; la lecture continue jusqu'à la fin du
fichier. Les corrélations décrivent des associations et non des relations causales.

La présentation de 15 minutes est disponible dans `presentation.html` (navigation
avec les flèches du clavier; les notes orateur sont dépliables sous chaque diapositive).

## Données et attribution

Les données proviennent du jeu Automobile de Jeffrey Schlimmer, publié dans le
UCI Machine Learning Repository en 1985. Elles sont distribuées sous licence
Creative Commons Attribution 4.0 (CC BY 4.0).

Source : [UCI Machine Learning Repository — Automobile](https://archive.ics.uci.edu/dataset/10/automobile)  
DOI : <https://doi.org/10.24432/C5B01C>
