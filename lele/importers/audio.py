"""Importer pour les fichiers audio avec transcription."""

from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType


class AudioImporter(BaseImporter):
    """Importe les fichiers audio avec transcription optionnelle."""

    source_type = SourceType.AUDIO

    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        transcribe: bool = True,
        whisper_model: str = "medium",
        language: Optional[str] = None,
        **options,
    ) -> ImportResult:
        """
        Importe un fichier audio.

        Args:
            file_path: Chemin du fichier audio
            project_files_path: Dossier du projet
            transcribe: Si True, transcrit l'audio en texte
            whisper_model: Modèle Whisper à utiliser
            language: Code de langue (None pour auto-détection)
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
            self.report_progress(0.1, "Analyse du fichier audio...")

            # Extraire les métadonnées audio
            audio_meta = self._get_audio_metadata(file_path)
            extra_metadata.update(audio_meta)

            self.report_progress(0.2, "Copie du fichier...")

            # Copier dans le projet
            dest_path = self.copy_to_project(file_path, project_files_path)

            # Transcription si demandée
            if transcribe:
                self.report_progress(0.3, f"Chargement du modèle {whisper_model}...")

                try:
                    transcript_result = self._transcribe(
                        file_path, whisper_model, language
                    )
                    content = transcript_result["text"]
                    extra_metadata["transcription"] = {
                        "model": whisper_model,
                        "language_detected": transcript_result.get("language"),
                        "segments": transcript_result.get("segments", []),
                    }
                    self.report_progress(0.9, "Transcription terminée")

                except ImportError:
                    warnings.append(
                        "Whisper non installé. Installez-le avec: pip install openai-whisper"
                    )
                except Exception as e:
                    warnings.append(f"Erreur de transcription: {e}")

            self.report_progress(0.95, "Création de la source...")

            # Créer la source
            metadata = self.get_file_metadata(file_path)
            metadata.update(extra_metadata)

            source = Source(
                name=file_path.stem,
                type=SourceType.AUDIO,
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

    def _get_audio_metadata(self, file_path: Path) -> dict:
        """Extrait les métadonnées d'un fichier audio."""
        metadata = {}

        try:
            from mutagen import File as MutagenFile

            audio = MutagenFile(str(file_path))
            if audio is not None:
                metadata["duration"] = getattr(audio.info, "length", None)
                metadata["sample_rate"] = getattr(audio.info, "sample_rate", None)
                metadata["channels"] = getattr(audio.info, "channels", None)
                metadata["bitrate"] = getattr(audio.info, "bitrate", None)

                # Tags
                if hasattr(audio, "tags") and audio.tags:
                    tags = {}
                    for key in audio.tags.keys():
                        try:
                            value = str(audio.tags[key])
                            tags[str(key)] = value
                        except Exception:
                            pass
                    if tags:
                        metadata["tags"] = tags

        except ImportError:
            pass
        except Exception:
            pass

        return metadata

    def _transcribe(
        self, file_path: Path, model_name: str, language: Optional[str]
    ) -> dict:
        """Transcrit un fichier audio avec Whisper."""
        import whisper

        self.report_progress(0.4, f"Chargement du modèle {model_name}...")
        model = whisper.load_model(model_name)

        self.report_progress(0.5, "Transcription en cours...")

        options = {}
        if language:
            options["language"] = language

        result = model.transcribe(str(file_path), **options)

        # Simplifier les segments pour le stockage
        simplified_segments = []
        for seg in result.get("segments", []):
            simplified_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            })

        return {
            "text": result["text"].strip(),
            "language": result.get("language"),
            "segments": simplified_segments,
        }

    def get_transcript_with_timestamps(self, source: Source) -> str:
        """Retourne la transcription avec timestamps."""
        segments = source.metadata.get("transcription", {}).get("segments", [])
        if not segments:
            return source.content or ""

        lines = []
        for seg in segments:
            start = self._format_timestamp(seg["start"])
            end = self._format_timestamp(seg["end"])
            lines.append(f"[{start} -> {end}] {seg['text']}")

        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Formate un timestamp en HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
