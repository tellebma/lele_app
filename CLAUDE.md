# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lele is a Qualitative Data Analysis (QDA) application inspired by NVivo, developed in Python with a Tkinter-based GUI. Documentation and UI are in French.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main application
python main.py

# Run standalone audio transcription tools
python gui.py          # GUI transcription interface
python transcribe.py   # CLI transcription tool
```

## Architecture

### Entry Points
- `main.py` - Launches the main QDA application (`lele.ui.MainWindow`)
- `gui.py` / `transcribe.py` - Standalone audio transcription using Whisper

### Package Structure (`lele/`)

**Models** (`lele/models/`) - Data layer with SQLite persistence:
- `project.py` - Project container, manages SQLite database (project.db)
- `source.py` - Imported documents/media (supports 11 types: TEXT, PDF, WORD, AUDIO, VIDEO, IMAGE, etc.)
- `node.py` - Hierarchical coding nodes with color coding
- `coding.py` - CodeReference links nodes to text spans in sources
- `memo.py` - Memos and annotations linked to sources/nodes
- `case.py` - Cases, classifications, and typed attributes

**Importers** (`lele/importers/`) - Factory pattern via `get_importer()`:
- Text: .txt, .md, .rtf, .pdf, .docx, .odt
- Audio: .mp3, .wav, .m4a, .flac (with Whisper transcription)
- Video: .mp4, .avi, .mov, .mkv
- Image: .jpg, .png, .gif, .bmp, .tiff
- Spreadsheet: .xlsx, .xls, .csv, .ods
- Bibliography: .ris, .bib (RIS, BibTeX)
- QDA Interchange: .qdpx (REFI-QDA standard)

**Analysis** (`lele/analysis/`):
- `search.py` - Full-text search using SQLite FTS5
- `query.py` - Boolean coding queries (AND, OR, NOT, NEAR, PRECEDED_BY)
- `matrix.py` - Cross-tabulation analysis (Nodes × Sources)
- `auto_coding/` - Automatic theme detection (see Auto-Coding Module below)

**Visualization** (`lele/visualization/`):
- `wordcloud_viz.py` - Word clouds from coded text
- `charts.py` - Bar/pie charts with matplotlib
- `mindmap.py` - Hierarchical node tree visualization
- `sociogram.py` - Co-occurrence networks with NetworkX

**UI** (`lele/ui/`):
- `main_window.py` - Main Tkinter application shell with context menus
- `dialogs/` - Modal dialog boxes (transcription, auto-coding, LLM settings)
- `panels/` - Sidebar panels (Sources, Nodes, Cases, Memos)
- `widgets/` - Custom UI components

**Utils** (`lele/utils/`):
- `settings.py` - SettingsManager singleton for user preferences (~/.lele/settings.json)

### Database

Projects are stored as directories containing:
- `project.json` - Metadata
- `project.db` - SQLite database with FTS5 indexes for search
- `files/` - Imported file copies

Key tables: `sources`, `nodes`, `code_references`, `memos`, `annotations`, `cases`, `classifications`, `attributes`

### Auto-Coding Module (`lele/analysis/auto_coding/`)

Automatic theme detection and node creation using NLP/ML:

**Pipeline**: Segmentation → Embeddings → Clustering → Labeling → Proposals

- `models.py` - Dataclasses: `Segment`, `NodeProposal`, `AutoCodingConfig`, `AutoCodingResult`
- `embeddings.py` - Sentence-transformers vectorization with cache, CUDA/MPS detection
- `clustering.py` - UMAP dimensionality reduction + HDBSCAN clustering
- `labeling.py` - Theme naming via LLM (Ollama local) or keyword extraction fallback
- `engine.py` - Pipeline orchestration with progress callbacks and logging

**UI Entry Points**:
- Button "🔮 Auto" in Nodes panel
- Menu: Codage → "Détection automatique de nœuds..."
- Settings: Paramètres → "IA / LLM local..."

**Configuration** (stored in `~/.lele/settings.json`):
- `llm_provider`: "ollama" or "none"
- `llm_model`: Ollama model name (default: "mistral")
- `ollama_url`: Ollama server URL
- `autocoding_embedding_model`: sentence-transformers model
- `autocoding_max_themes`, `autocoding_min_cluster_size`, `autocoding_confidence_threshold`

### Node Management UX

**Context Menus**:
- Right-click on text: Code with node, create node from selection
- Right-click on node: Rename, change color, add child, delete

**Quick Actions**:
- Double-click on node (with text selected): Instantly code selection
- Ctrl+Shift+K: Create node from selection and code
- F2: Rename selected node
- Delete: Delete selected node (when tree focused)

## Key Dependencies

- **GUI**: tkinterdnd2 (drag & drop)
- **Transcription**: openai-whisper, imageio-ffmpeg
- **Documents**: pypdf, python-docx
- **Data**: pandas, openpyxl
- **Visualization**: matplotlib, wordcloud, networkx
- **Audio metadata**: mutagen
- **Auto-coding**: sentence-transformers, umap-learn, hdbscan
- **LLM local** (optional): Ollama (external, install from ollama.ai)

## Code Conventions

- Type hints throughout (Python 3.10+ syntax with `|` union types)
- Dataclasses for models
- French docstrings and comments
- Factory patterns for importers and exporters
- Singleton pattern for settings management
- Threading for async operations (transcription, auto-coding)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New project |
| Ctrl+O | Open project |
| Ctrl+S | Save project |
| Ctrl+K | Code selection with selected node |
| Ctrl+Shift+N | New node |
| Ctrl+Shift+K | Quick code (create node from selection) |
| Ctrl+F | Search |
| F2 | Rename selected node |
| Delete | Delete selected node |
| Ctrl+Q | Quit |
