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

### Transcription audio automatique
- Moteur Whisper (OpenAI) intégré
- Choix du modèle (tiny → large)
- Détection automatique de la langue
- Support GPU (CUDA/Apple Silicon)

### Codage et analyse
- Création de nœuds (codes) hiérarchiques avec couleurs
- Codage de passages de texte
- Mémos et annotations
- Cas et classifications avec attributs personnalisés

### Détection automatique de thèmes (Auto-codage)
- Analyse NLP avec sentence-transformers
- Clustering automatique (UMAP + HDBSCAN)
- Nommage des thèmes via LLM local (Ollama) ou mots-clés
- Prévisualisation et validation avant création

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
- Ou clic droit sur un nœud > "Ajouter un sous-nœud"
- Définir nom, couleur et description

### 4. Coder du texte
**Méthode classique :**
1. Sélectionner une source
2. Sélectionner un nœud
3. Surligner le texte à coder
4. `Ctrl+K` ou bouton "Coder"

**Méthode rapide :**
- Surligner du texte → clic droit → "Coder avec" → choisir un nœud
- Ou double-clic sur un nœud (avec du texte sélectionné)

**Créer et coder en même temps :**
- Surligner du texte → `Ctrl+Shift+K` → le nom est pré-rempli

### 5. Détection automatique
- Cliquer sur "🔮 Auto" dans le panneau Nœuds
- Ou `Codage > Détection automatique de nœuds`
- Sélectionner les sources à analyser
- Valider les thèmes proposés

### 6. Visualiser
Menu `Analyse` > choisir une visualisation

## Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+N` | Nouveau projet |
| `Ctrl+O` | Ouvrir projet |
| `Ctrl+S` | Sauvegarder |
| `Ctrl+K` | Coder la sélection |
| `Ctrl+Shift+N` | Nouveau nœud |
| `Ctrl+Shift+K` | Créer nœud depuis sélection et coder |
| `Ctrl+F` | Rechercher |
| `F2` | Renommer le nœud sélectionné |
| `Suppr` | Supprimer le nœud sélectionné |
| `Ctrl+Q` | Quitter |

## Menus contextuels (clic droit)

### Sur le texte
- 🏷️ Coder avec... (liste des nœuds)
- ➕ Nouveau nœud depuis la sélection
- 📋 Copier
- 🔍 Rechercher

### Sur un nœud
- ✏️ Renommer
- 🎨 Changer la couleur
- ➕ Ajouter un sous-nœud
- 🗑️ Supprimer

## Structure d'un projet

```
mon_projet/
├── project.json    # Métadonnées
├── project.db      # Base de données SQLite
└── files/          # Fichiers importés
```

## Configuration IA (optionnel)

Pour utiliser le nommage automatique des thèmes via LLM local :

1. Installer [Ollama](https://ollama.ai)
2. Télécharger un modèle : `ollama pull mistral`
3. Dans Lele : `Paramètres > IA / LLM local`
4. Configurer l'URL et le modèle

Sans Ollama, les thèmes sont nommés par extraction de mots-clés.

## Dépendances principales

- Python 3.10+
- tkinter / tkinterdnd2 (interface)
- openai-whisper (transcription)
- sentence-transformers (embeddings)
- umap-learn, hdbscan (clustering)
- matplotlib, wordcloud, networkx (visualisations)

## Licence

MIT License
