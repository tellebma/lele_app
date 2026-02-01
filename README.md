# Lele - Analyse Qualitative de Données

Application d'analyse qualitative de données (QDA) inspirée de NVivo, développée en Python.

## Installation

```bash
# Cloner le projet
git clone <url-du-repo>
cd lele_app

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python main.py
```

## Fonctionnalités principales

### Import de données
- **Documents** : TXT, PDF, Word (.docx), RTF
- **Média** : Audio (MP3, WAV, FLAC), Vidéo (MP4, AVI, MOV), Images (JPG, PNG)
- **Données** : Excel, CSV, fichiers statistiques
- **Bibliographie** : RIS, BibTeX, EndNote
- **Interopérabilité** : Import/Export REFI-QDA (.qdpx)

### Codage et analyse
- Création de nœuds (codes) hiérarchiques
- Codage de passages de texte
- Mémos et annotations
- Cas et classifications avec attributs personnalisés

### Visualisations
- Nuage de mots
- Carte mentale des codes
- Sociogramme (co-occurrences)
- Matrices et histogrammes

### Recherche
- Recherche full-text dans les sources
- Requêtes de codage (AND, OR, NOT, proximité)
- Analyse matricielle

## Guide rapide

### 1. Créer un projet
`Fichier > Nouveau projet` ou `Ctrl+N`

### 2. Importer des fichiers
- Glisser-déposer des fichiers dans le panneau Sources
- Ou `Fichier > Importer`

### 3. Créer des codes
- Clic sur `+` dans le panneau Nœuds
- Définir nom, couleur et description

### 4. Coder du texte
1. Sélectionner une source
2. Sélectionner un nœud
3. Surligner le texte à coder
4. `Ctrl+K` ou bouton "Coder"

### 5. Visualiser
Menu `Analyse` > choisir une visualisation

## Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+N` | Nouveau projet |
| `Ctrl+O` | Ouvrir projet |
| `Ctrl+S` | Sauvegarder |
| `Ctrl+K` | Coder la sélection |
| `Ctrl+F` | Rechercher |
| `Ctrl+Q` | Quitter |

## Structure d'un projet

```
mon_projet/
├── project.json    # Métadonnées
├── project.db      # Base de données SQLite
└── files/          # Fichiers importés
```

## Licence

MIT License
