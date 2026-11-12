# Guide de test AutoStat

Ce guide explique comment lancer les différentes phases, la suite de tests et
les deux vérifications de robustesse demandées dans la consigne.

## 1. Ouvrir le terminal à la racine du projet

Dans PowerShell, exécuter :

```powershell
Set-Location 'C:\Users\Ryan\Documents\ESIEE-IT\Cours_cybersécurité\python\Projet\Projet_code'
```

Les commandes ci-dessous sont à lancer depuis ce dossier, où se trouve
`main.py`.

## 2. Installer la dépendance

À faire une seule fois si NumPy n'est pas déjà installé :

```powershell
python -m pip install -r requirements.txt
```

## 3. Tester chaque phase

```powershell
python main.py phase1
python main.py phase2
python main.py phase3
python main.py phase4
```

- **Phase 1** affiche les 26 variables, la fiche du premier véhicule et la
  répartition des carrosseries.
- **Phase 2** affiche les effectifs par carburant, les prix moyens par type de
  roues motrices, le classement des marques et l'aperçu NumPy.
- **Phase 3** compare les résultats du moteur Python et de NumPy, puis affiche
  les corrélations avec le prix. Le chronométrage varie selon l'ordinateur.
- **Phase 4** valide les données réelles et génère
  `sorties\vehicules_decodes.csv` et `sorties\rapport.json`.

Pour le fichier UCI fourni, la phase 4 doit indiquer 205 lignes valides et
aucun rejet. Les prix manquants sont comptabilisés, sans être considérés comme
des lignes invalides.

## 4. Lancer les tests automatisés

```powershell
python -m unittest -v
```

La suite vérifie notamment les conversions textuelles, les structures NumPy,
l'équivalence des moteurs, la lecture du fichier ZIP et du fichier extrait,
ainsi que les erreurs de données.

## 5. Tester l'échantillon corrompu

```powershell
python main.py phase4 --fichier donnees\echantillon_corrompu.data -v
```

L'option `-v` affiche les avertissements expliquant les rejets. Le résultat
attendu est **2 lignes valides et 6 rejets** : doublon, deux codes hors
dictionnaire, prix non numérique, nombre de colonnes incorrect et prix négatif.
Le programme continue à lire le fichier après chaque ligne rejetée.

## 6. Tester un fichier absent

```powershell
python main.py phase4 --fichier absent.zip
```

`absent.zip` est volontairement absent : il ne faut pas le créer. Le programme
doit afficher une erreur semblable à :

```text
Erreur : Fichier introuvable : absent.zip
```

Le code de retour attendu est `1`. Pour le vérifier dans PowerShell,
immédiatement après la commande :

```powershell
$LASTEXITCODE
```

## 7. Résultats générés

Après `python main.py phase4`, consulter :

- `sorties\vehicules_decodes.csv` : données lisibles, unités converties et
  séparateur `;`.
- `sorties\rapport.json` : qualité des données, manquants, bilan et date de
  génération.
