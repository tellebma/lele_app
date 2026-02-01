# Guide d'utilisation de Lele

## Table des matières

1. [Démarrage](#démarrage)
2. [Gestion des projets](#gestion-des-projets)
3. [Import de données](#import-de-données)
4. [Codage](#codage)
5. [Mémos et annotations](#mémos-et-annotations)
6. [Recherche](#recherche)
7. [Visualisations](#visualisations)
8. [Export](#export)

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
- Choix du modèle (tiny → large)
- Détection automatique de la langue

**Images :**
- OCR optionnel (extraction de texte)

**Tableurs :**
- Sélection de la feuille
- Définition de la ligne d'en-tête

---

## Codage

### Créer un nœud (code)

1. Dans le panneau "Nœuds", cliquer sur `+`
2. Entrer le nom du nœud
3. Choisir une couleur
4. (Optionnel) Ajouter une description

### Hiérarchie des nœuds

- Sélectionner un nœud parent avant de créer un enfant
- Utiliser le bouton dossier pour créer des catégories

### Coder un passage

1. Ouvrir une source (double-clic)
2. Sélectionner un nœud dans le panneau Nœuds
3. Surligner le texte à coder
4. Appuyer sur `Ctrl+K` ou cliquer sur "Coder"

Le passage codé sera surligné avec la couleur du nœud.

### Voir les références d'un nœud

- Double-clic sur un nœud pour voir toutes ses références
- Les références apparaissent dans le panneau du bas

### Supprimer un codage

- Sélectionner le codage dans le panneau "Codages"
- Clic droit > Supprimer

---

## Mémos et annotations

### Créer un mémo

1. Cliquer sur le bouton "Mémo" dans la barre d'outils
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

## Conseils pratiques

### Organisation des codes

1. Commencer par des codes larges
2. Affiner avec des sous-codes
3. Utiliser des couleurs cohérentes par thème

### Bonnes pratiques

- **Sauvegarder régulièrement** le projet
- **Documenter** les décisions de codage dans les mémos
- **Utiliser les annotations** pour les réflexions rapides
- **Réviser les codes** périodiquement

### Performance

- Pour les gros fichiers audio/vidéo, utiliser le modèle Whisper "small"
- Fermer les projets non utilisés
- Les visualisations peuvent prendre du temps sur de gros corpus

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

### Erreur d'encodage sur les fichiers texte

L'application essaie automatiquement UTF-8, Latin-1, et CP1252. Si le problème persiste, convertir le fichier en UTF-8 avant import.
