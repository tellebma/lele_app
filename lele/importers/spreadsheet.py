"""Importer pour les fichiers tableur (Excel, CSV, etc.)."""

from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType


class SpreadsheetImporter(BaseImporter):
    """Importe les fichiers tableur."""

    source_type = SourceType.SPREADSHEET

    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        sheet_name: Optional[str] = None,
        header_row: int = 0,
        **options,
    ) -> ImportResult:
        """
        Importe un fichier tableur.

        Args:
            file_path: Chemin du fichier
            project_files_path: Dossier du projet
            sheet_name: Nom de la feuille à importer (None = toutes)
            header_row: Ligne d'en-tête (0-indexed)
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        valid, error = self.validate_file(file_path)
        if not valid:
            return ImportResult(success=False, error=error)

        warnings = []
        extra_metadata = {}

        try:
            self.report_progress(0.1, "Lecture du fichier...")

            ext = file_path.suffix.lower()

            if ext == ".csv":
                content, sheet_meta = self._read_csv(file_path, header_row)
            else:
                content, sheet_meta = self._read_excel(
                    file_path, sheet_name, header_row
                )

            extra_metadata.update(sheet_meta)

            self.report_progress(0.6, "Copie du fichier...")

            # Copier dans le projet
            dest_path = self.copy_to_project(file_path, project_files_path)

            self.report_progress(0.9, "Création de la source...")

            # Créer la source
            metadata = self.get_file_metadata(file_path)
            metadata.update(extra_metadata)

            source = Source(
                name=file_path.stem,
                type=SourceType.SPREADSHEET,
                file_path=str(dest_path),
                content=content,
                metadata=metadata,
            )

            self.report_progress(1.0, "Import terminé")

            return ImportResult(
                success=True,
                source=source,
                warnings=warnings,
                metadata=metadata,
            )

        except Exception as e:
            return ImportResult(success=False, error=str(e))

    def _read_csv(self, file_path: Path, header_row: int) -> tuple[str, dict]:
        """Lit un fichier CSV."""
        try:
            import pandas as pd

            df = pd.read_csv(file_path, header=header_row)
            content = df.to_string()
            metadata = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
            }
            return content, metadata

        except ImportError:
            # Fallback sans pandas
            import csv

            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if header_row < len(rows):
                headers = rows[header_row]
                data_rows = rows[header_row + 1:]
            else:
                headers = []
                data_rows = rows

            # Convertir en texte
            lines = []
            if headers:
                lines.append("\t".join(headers))
                lines.append("-" * 40)
            for row in data_rows:
                lines.append("\t".join(row))

            content = "\n".join(lines)
            metadata = {
                "row_count": len(data_rows),
                "column_count": len(headers) if headers else (len(rows[0]) if rows else 0),
                "columns": headers,
            }
            return content, metadata

    def _read_excel(
        self, file_path: Path, sheet_name: Optional[str], header_row: int
    ) -> tuple[str, dict]:
        """Lit un fichier Excel."""
        try:
            import pandas as pd

            # Lire toutes les feuilles ou une seule
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
                sheets_data = {sheet_name: df}
            else:
                sheets_data = pd.read_excel(
                    file_path, sheet_name=None, header=header_row
                )

            content_parts = []
            sheets_info = {}

            for name, df in sheets_data.items():
                content_parts.append(f"=== Feuille: {name} ===\n")
                content_parts.append(df.to_string())
                content_parts.append("\n\n")
                sheets_info[name] = {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                }

            content = "".join(content_parts)
            metadata = {
                "sheet_count": len(sheets_data),
                "sheets": sheets_info,
            }
            return content, metadata

        except ImportError:
            raise ImportError(
                "Installez pandas et openpyxl pour lire les fichiers Excel: "
                "pip install pandas openpyxl"
            )

    def import_survey_data(
        self,
        file_path: Path,
        project_files_path: Path,
        response_id_column: str = None,
        question_columns: list[str] = None,
        **options,
    ) -> ImportResult:
        """
        Importe des données de sondage avec structure spéciale.

        Args:
            file_path: Chemin du fichier
            project_files_path: Dossier du projet
            response_id_column: Colonne identifiant les réponses
            question_columns: Colonnes contenant les questions
        """
        result = self.import_file(file_path, project_files_path, **options)

        if result.success and result.source:
            # Enrichir les métadonnées avec les infos de sondage
            result.source.metadata["survey"] = {
                "response_id_column": response_id_column,
                "question_columns": question_columns,
            }

        return result

    def get_dataframe(self, source: Source):
        """Retourne les données comme DataFrame pandas."""
        try:
            import pandas as pd

            if not source.file_path:
                return None

            file_path = Path(source.file_path)
            ext = file_path.suffix.lower()

            if ext == ".csv":
                return pd.read_csv(file_path)
            else:
                return pd.read_excel(file_path)

        except ImportError:
            return None
