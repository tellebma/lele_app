"""Importer pour les fichiers image."""

from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType


class ImageImporter(BaseImporter):
    """Importe les fichiers image avec OCR optionnel."""

    source_type = SourceType.IMAGE

    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        ocr: bool = False,
        ocr_language: str = "fra+eng",
        **options,
    ) -> ImportResult:
        """
        Importe un fichier image.

        Args:
            file_path: Chemin du fichier image
            project_files_path: Dossier du projet
            ocr: Si True, extrait le texte par OCR
            ocr_language: Langues pour l'OCR (format tesseract)
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        valid, error = self.validate_file(file_path)
        if not valid:
            return ImportResult(success=False, error=error)

        warnings = []
        content = ""
        extra_metadata = {}

        try:
            self.report_progress(0.1, "Analyse de l'image...")

            # Extraire les métadonnées image
            image_meta = self._get_image_metadata(file_path)
            extra_metadata.update(image_meta)

            self.report_progress(0.3, "Copie du fichier...")

            # Copier dans le projet
            dest_path = self.copy_to_project(file_path, project_files_path)

            # OCR si demandé
            if ocr:
                self.report_progress(0.5, "Extraction du texte (OCR)...")

                try:
                    content = self._extract_text_ocr(file_path, ocr_language)
                    extra_metadata["ocr"] = {
                        "language": ocr_language,
                        "extracted": True,
                    }
                except ImportError as e:
                    warnings.append(str(e))
                except Exception as e:
                    warnings.append(f"Erreur OCR: {e}")

            self.report_progress(0.9, "Création de la source...")

            # Créer la source
            metadata = self.get_file_metadata(file_path)
            metadata.update(extra_metadata)

            source = Source(
                name=file_path.stem,
                type=SourceType.IMAGE,
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

    def _get_image_metadata(self, file_path: Path) -> dict:
        """Extrait les métadonnées d'une image."""
        metadata = {}

        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                metadata["mode"] = img.mode

                # Extraire les données EXIF
                exif_data = img._getexif()
                if exif_data:
                    exif = {}
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        # Convertir les valeurs non sérialisables
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8", errors="ignore")
                            except Exception:
                                value = str(value)
                        exif[str(tag)] = str(value)
                    metadata["exif"] = exif

        except ImportError:
            # Fallback basique
            pass
        except Exception:
            pass

        return metadata

    def _extract_text_ocr(self, file_path: Path, language: str) -> str:
        """Extrait le texte d'une image par OCR."""
        try:
            import pytesseract
            from PIL import Image

            with Image.open(file_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                text = pytesseract.image_to_string(img, lang=language)
                return text.strip()

        except ImportError:
            raise ImportError(
                "Installez pytesseract et Tesseract OCR: "
                "pip install pytesseract && sudo apt-get install tesseract-ocr"
            )

    def create_thumbnail(
        self, source: Source, size: tuple[int, int] = (200, 200)
    ) -> Optional[str]:
        """Crée une miniature de l'image."""
        if not source.file_path:
            return None

        try:
            from PIL import Image

            file_path = Path(source.file_path)
            thumb_path = file_path.parent / f"{file_path.stem}_thumb{file_path.suffix}"

            with Image.open(file_path) as img:
                img.thumbnail(size)
                img.save(thumb_path)

            return str(thumb_path)

        except Exception:
            return None
