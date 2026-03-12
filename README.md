# Invoice Maker (Demo)

Outil Python simple pour générer une facture **de démo** (HTML + image PNG) avec un watermark géant `DEMO`.

Ce guide est fait pour quelqu'un qui part de zéro.

## 1) Ce qu'il faut installer

### macOS
- `Python 3` (version 3.9+ recommandée)
- `pip` (gestionnaire de paquets Python, souvent déjà inclus)

Vérifie dans le Terminal:

```bash
python3 --version
python3 -m pip --version
```

Si `python3` ne fonctionne pas, installe Python depuis [python.org](https://www.python.org/downloads/).

## 2) Ouvrir le projet

Dans le Terminal:

```bash
cd /Users/imrane/Desktop/Code/Invoice-maker
```

## 3) Installer la dépendance pour exporter en PNG

Le script génère toujours le HTML.  
Pour la capture PNG automatique, il faut installer Playwright + Chromium:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## 4) Lancer l'outil

```bash
python3 invoice_tool.py
```

Tu verras un menu:
- `1` Créer un profil
- `2` Charger un profil
- `3` Générer la facture (HTML + PNG)
- `0` Quitter

## 5) Premier usage recommandé

1. Lance `python3 invoice_tool.py`
2. Tape `1` pour créer un profil
3. Remplis les champs demandés (`Nom`, `Ville`, `Prix`, `Date`, etc.)
4. Mets ton lien PNG dans `URL du logo d'en-tête (PNG recommandé)` si tu veux un logo perso
5. Sauvegarde le profil
6. Tape `3` pour générer la facture

## 6) Fichiers générés

- Script principal: `/Users/imrane/Desktop/Code/Invoice-maker/invoice_tool.py`
- Profils sauvegardés: `/Users/imrane/Desktop/Code/Invoice-maker/profiles/*.json`
- HTML généré: `/Users/imrane/Desktop/Code/Invoice-maker/output/invoice.html`
- PNG généré: `/Users/imrane/Desktop/Code/Invoice-maker/output/invoice.png`

## 7) Réutiliser un modèle

1. Lance le script
2. Tape `2` (charger un profil)
3. Choisis le profil
4. Modifie seulement les champs voulus
5. Génère à nouveau avec `3`

## 8) Dépannage rapide

### "PNG non généré: Playwright n'est pas installé"
Relance:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

### La date est refusée
Utilise le format exact: `jj/mm/aa`  
Exemple: `08/04/26`

### Le prix est refusé
Exemples valides:
- `499.99`
- `499,99`

### Je n'ai que le HTML
C'est normal si Chromium/Playwright n'est pas disponible.  
Le fichier HTML est déjà prêt dans `output/invoice.html`.

## 9) Important

- Ce projet est pour la **démo** (placeholder), pas pour un usage officiel.
# apple-invoice-maker
# apple-invoice-maker
# apple-invoice-maker
# apple-invoice-maker
