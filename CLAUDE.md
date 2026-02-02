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

**Visualization** (`lele/visualization/`):
- `wordcloud_viz.py` - Word clouds from coded text
- `charts.py` - Bar/pie charts with matplotlib
- `mindmap.py` - Hierarchical node tree visualization
- `sociogram.py` - Co-occurrence networks with NetworkX

**UI** (`lele/ui/`):
- `main_window.py` - Main Tkinter application shell
- `dialogs/` - Modal dialog boxes
- `panels/` - Sidebar panels (Sources, Nodes, Cases, Memos)
- `widgets/` - Custom UI components

### Database

Projects are stored as directories containing:
- `project.json` - Metadata
- `project.db` - SQLite database with FTS5 indexes for search
- `files/` - Imported file copies

Key tables: `sources`, `nodes`, `code_references`, `memos`, `annotations`, `cases`, `classifications`, `attributes`

## Key Dependencies

- **GUI**: tkinterdnd2 (drag & drop)
- **Transcription**: openai-whisper
- **Documents**: pypdf, python-docx
- **Data**: pandas, openpyxl
- **Visualization**: matplotlib, wordcloud, networkx
- **Audio metadata**: mutagen

## Code Conventions

- Type hints throughout (Python 3.10+ syntax with `|` union types)
- Dataclasses for models
- French docstrings and comments
- Factory patterns for importers and exporters
