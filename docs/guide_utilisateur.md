# Guide d'utilisation de Lele

## Table des matières

1. [Démarrage](#démarrage)
2. [Gestion des projets](#gestion-des-projets)
3. [Import de données](#import-de-données)
4. [Codage](#codage)
5. [Détection automatique de thèmes](#détection-automatique-de-thèmes)
6. [Mémos et annotations](#mémos-et-annotations)
7. [Recherche](#recherche)
8. [Visualisations](#visualisations)
9. [Export](#export)
10. [Raccourcis clavier](#raccourcis-clavier)
11. [Dépannage](#dépannage)

---

## Démarrage

### Lancement de l'application

```bash
python main.py
```

### Interface principale

L'interface est divisée en plusieurs zones :

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu et barre d'outils                                         │
├───────────┬─────────────────────────────────┬───────────────────┤
│           │                                 │                   │
│  Sources  │     Zone de contenu             │   Propriétés      │
│  Nœuds    │     (document actif)            │   Codages         │
│  Cas      │                                 │   Annotations     │
│  Mémos    │                                 │                   │
│           ├─────────────────────────────────┤                   │
│           │  Résultats (recherche, refs)    │                   │
├───────────┴─────────────────────────────────┴───────────────────┤
│  Barre de statut                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Gestion des projets

### Créer un nouveau projet

1. `Fichier > Nouveau projet` (ou `Ctrl+N`)
2. Entrer le nom du projet
3. Choisir l'emplacement
4. Cliquer sur "Créer"

Un dossier sera créé contenant :
- `project.json` : métadonnées du projet
- `project.db` : base de données
- `files/` : fichiers importés

### Ouvrir un projet existant

1. `Fichier > Ouvrir projet` (ou `Ctrl+O`)
2. Sélectionner le dossier du projet

Les projets récents sont accessibles via `Fichier > Projets récents`.

### Sauvegarder

- `Fichier > Sauvegarder` (ou `Ctrl+S`)
- La sauvegarde est automatique lors de la fermeture

---

## Import de données

### Formats supportés

| Catégorie | Extensions |
|-----------|------------|
| Texte | .txt, .md, .rtf |
| Documents | .pdf, .doc, .docx, .odt |
| Audio | .mp3, .wav, .m4a, .flac, .ogg |
| Vidéo | .mp4, .avi, .mov, .mkv |
| Images | .jpg, .png, .gif, .bmp, .tiff |
| Tableurs | .xlsx, .xls, .csv, .ods |
| Bibliographie | .ris, .bib, .enw |
| QDA | .qdpx (REFI-QDA) |

### Méthodes d'import

**Glisser-déposer :**
- Glisser les fichiers directement dans le panneau Sources

**Menu :**
- `Fichier > Importer`
- Sélectionner un ou plusieurs fichiers

### Options d'import

**Audio/Vidéo :**
- Transcription automatique avec Whisper
- Choix du modèle (tiny, base, small, medium, large)
- Détection automatique de la langue ou sélection manuelle
- Paramètres dans `Paramètres > Transcription audio/vidéo`

**Images :**
- OCR optionnel (extraction de texte)

**Tableurs :**
- Sélection de la feuille
- Définition de la ligne d'en-tête

---

## Codage

### Créer un nœud (code)

**Méthode standard :**
1. Dans le panneau "Nœuds", cliquer sur `+`
2. Entrer le nom du nœud
3. Choisir une couleur parmi la palette (16 couleurs)
4. (Optionnel) Ajouter une description
5. Cliquer sur "Créer"

**Via le menu contextuel :**
- Clic droit sur un nœud > "➕ Ajouter un sous-nœud"

**Raccourci :** `Ctrl+Shift+N`

### Hiérarchie des nœuds

- Les nœuds peuvent avoir des sous-nœuds (enfants)
- Sélectionner un nœud parent avant de créer un enfant
- Utiliser le bouton dossier `📁` pour créer des catégories

### Gérer les nœuds

**Renommer :**
- Clic droit > "✏️ Renommer"
- Ou sélectionner le nœud et appuyer sur `F2`

**Changer la couleur :**
- Clic droit > "🎨 Changer la couleur"
- Choisir parmi la palette de 16 couleurs

**Supprimer :**
- Clic droit > "🗑️ Supprimer"
- Ou sélectionner le nœud et appuyer sur `Suppr`

### Coder un passage

**Méthode classique :**
1. Ouvrir une source (double-clic)
2. Sélectionner un nœud dans le panneau Nœuds
3. Surligner le texte à coder
4. Appuyer sur `Ctrl+K` ou cliquer sur "🏷️ Coder"

**Méthode rapide avec le menu contextuel :**
1. Surligner le texte à coder
2. Clic droit sur le texte
3. "🏷️ Coder avec" > choisir un nœud

**Méthode ultra-rapide par double-clic :**
1. Surligner le texte à coder
2. Double-cliquer sur le nœud souhaité dans le panneau Nœuds

**Créer un nœud et coder en même temps :**
1. Surligner le texte
2. `Ctrl+Shift+K` ou clic droit > "➕ Nouveau nœud depuis la sélection"
3. Le nom est pré-rempli avec le début du texte sélectionné
4. Ajuster si nécessaire, puis "Créer"

Le passage codé sera surligné avec la couleur du nœud.

### Voir les références d'un nœud

- Double-clic sur un nœud pour voir toutes ses références
- Les références apparaissent dans le panneau du bas

### Supprimer un codage

- Sélectionner le codage dans le panneau "Codages"
- Clic droit > Supprimer

---

## Détection automatique de thèmes

Cette fonctionnalité analyse automatiquement vos sources pour détecter des thèmes récurrents et proposer des nœuds.

### Lancer l'analyse

1. Cliquer sur "🔮 Auto" dans le panneau Nœuds
2. Ou `Codage > Détection automatique de nœuds`

### Configuration

**Sources à analyser :**
- Cocher/décocher les sources à inclure
- Seules les sources avec du contenu textuel sont proposées

**Granularité de découpage :**
- **Paragraphe** (recommandé) : pour entretiens et textes structurés
- **Phrase** : pour textes denses
- **Fenêtre glissante** : pour textes longs sans structure

**Nombre max de thèmes :**
- Limite le nombre de thèmes détectés

**Nommage des thèmes (LLM) :**
- **Ollama (local)** : utilise un LLM local pour générer des noms
- **Mots-clés uniquement** : extrait les mots-clés les plus fréquents

### Paramètres avancés

- **Taille min. d'un cluster** : nombre minimum de segments pour former un thème
- **Seuil de confiance** : filtre les thèmes peu fiables
- Options d'exclusion et de fusion

### Résultats

1. Une fenêtre de prévisualisation affiche les thèmes détectés
2. Pour chaque thème :
   - Nom proposé
   - Couleur
   - Nombre de segments
   - Score de confiance
3. Vous pouvez :
   - Renommer un thème
   - Décocher les thèmes non pertinents
   - Voir les segments associés

### Validation

- Cliquer sur "Créer les nœuds sélectionnés"
- Les nœuds sont créés et les segments automatiquement codés

### Configuration IA

Pour un meilleur nommage des thèmes, configurer Ollama :

1. Installer [Ollama](https://ollama.ai)
2. Télécharger un modèle : `ollama pull mistral`
3. Dans Lele : `Paramètres > IA / LLM local`
4. Vérifier que l'URL est correcte (défaut: http://localhost:11434)
5. Sélectionner le modèle

---

## Mémos et annotations

### Créer un mémo

1. Cliquer sur le bouton "📝 Mémo" dans la barre d'outils
2. Entrer un titre
3. Rédiger le contenu
4. Sauvegarder

Les mémos peuvent être liés à :
- Une source spécifique
- Un nœud
- Le projet en général

### Annotations

Les annotations sont des notes courtes attachées à des passages spécifiques du texte.

1. Sélectionner du texte
2. Clic droit > Annoter
3. Entrer l'annotation

---

## Recherche

### Recherche simple

1. Utiliser la barre de recherche rapide (en haut)
2. Ou `Ctrl+F` pour la recherche avancée

### Types de recherche

**Texte simple :**
- Recherche dans toutes les sources et mémos

**Expression régulière :**
- Patterns avancés (ex: `erreur.*critique`)

### Requêtes de codage

Menu `Analyse > Requête de codage`

**Opérateurs disponibles :**

| Opérateur | Description | Exemple |
|-----------|-------------|---------|
| AND | Tous les codes présents | "stress" ET "travail" |
| OR | Au moins un code | "anxiété" OU "dépression" |
| NOT | Exclure un code | "problème" SAUF "résolu" |
| NEAR | Codes proches | "cause" PRÈS DE "effet" |

---

## Visualisations

### Nuage de mots

`Analyse > Nuage de mots`

Options :
- Sources à inclure
- Mots à exclure
- Nombre maximum de mots
- Palette de couleurs

### Carte mentale

`Analyse > Carte mentale`

Affiche la hiérarchie des nœuds avec :
- Taille proportionnelle aux références
- Couleurs des nœuds
- Export HTML interactif

### Sociogramme

`Analyse > Sociogramme`

Graphe des co-occurrences :
- Les nœuds qui apparaissent ensemble sont reliés
- L'épaisseur des liens = fréquence de co-occurrence

### Matrice

`Analyse > Matrice`

Types de matrices :
- **Nœuds × Sources** : fréquence des codes par source
- **Nœuds × Nœuds** : co-occurrences
- **Cas × Nœuds** : distribution par cas

---

## Export

### Export de visualisations

Chaque visualisation peut être sauvegardée :
- Format PNG
- Cliquer sur "Sauvegarder" dans la fenêtre

### Export REFI-QDA

Pour l'interopérabilité avec d'autres logiciels QDA :

`Fichier > Exporter > REFI-QDA`

Crée un fichier `.qdpx` compatible avec :
- NVivo
- ATLAS.ti
- MAXQDA
- Autres logiciels compatibles

---

## Raccourcis clavier

### Navigation et projets

| Raccourci | Action |
|-----------|--------|
| `Ctrl+N` | Nouveau projet |
| `Ctrl+O` | Ouvrir projet |
| `Ctrl+S` | Sauvegarder |
| `Ctrl+Q` | Quitter |

### Codage

| Raccourci | Action |
|-----------|--------|
| `Ctrl+K` | Coder la sélection avec le nœud actif |
| `Ctrl+Shift+N` | Nouveau nœud |
| `Ctrl+Shift+K` | Créer nœud depuis sélection et coder |
| `F2` | Renommer le nœud sélectionné |
| `Suppr` | Supprimer le nœud sélectionné |

### Recherche

| Raccourci | Action |
|-----------|--------|
| `Ctrl+F` | Rechercher |

### Actions rapides

- **Double-clic sur un nœud** (avec texte sélectionné) : coder immédiatement
- **Clic droit sur texte** : menu contextuel avec options de codage
- **Clic droit sur nœud** : menu contextuel pour gérer le nœud

---

## Dépannage

### L'import audio ne fonctionne pas

Vérifier que Whisper est installé :
```bash
pip install openai-whisper
```

### Le glisser-déposer ne fonctionne pas

Installer tkinterdnd2 :
```bash
pip install tkinterdnd2
```

### Les visualisations ne s'affichent pas

Vérifier les dépendances :
```bash
pip install matplotlib wordcloud networkx pillow
```

### La détection automatique échoue

Vérifier les dépendances NLP :
```bash
pip install sentence-transformers umap-learn hdbscan
```

### Ollama ne répond pas

1. Vérifier qu'Ollama est lancé
2. Vérifier l'URL dans `Paramètres > IA / LLM local`
3. Tester : `curl http://localhost:11434/api/tags`

### Erreur d'encodage sur les fichiers texte

L'application essaie automatiquement UTF-8, Latin-1, et CP1252. Si le problème persiste, convertir le fichier en UTF-8 avant import.

### L'application est lente avec de gros fichiers

- Pour la transcription : utiliser le modèle "small" au lieu de "large"
- Pour l'auto-codage : réduire le nombre de sources analysées
- Fermer les projets non utilisés

---

## Conseils pratiques

### Organisation des codes

1. Commencer par des codes larges
2. Affiner avec des sous-codes
3. Utiliser des couleurs cohérentes par thème
4. Utiliser la détection automatique pour découvrir des thèmes

### Bonnes pratiques

- **Sauvegarder régulièrement** le projet
- **Documenter** les décisions de codage dans les mémos
- **Utiliser les annotations** pour les réflexions rapides
- **Réviser les codes** périodiquement
- **Valider les thèmes automatiques** avant création

### Workflow recommandé

1. Importer toutes les sources
2. Lancer une première détection automatique
3. Valider et ajuster les thèmes proposés
4. Compléter manuellement avec des codes spécifiques
5. Utiliser les visualisations pour explorer les données
6. Rédiger des mémos d'analyse
