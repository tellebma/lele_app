"""Importer pour les fichiers vidéo."""

from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType


class VideoImporter(BaseImporter):
    """Importe les fichiers vidéo avec extraction audio et transcription."""

    source_type = SourceType.VIDEO

    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        transcribe: bool = True,
        whisper_model: str = "medium",
        language: Optional[str] = None,
        extract_frames: bool = False,
        frame_interval: int = 60,
        **options,
    ) -> ImportResult:
        """
        Importe un fichier vidéo.

        Args:
            file_path: Chemin du fichier vidéo
            project_files_path: Dossier du projet
            transcribe: Si True, transcrit l'audio
            whisper_model: Modèle Whisper à utiliser
            language: Code de langue
            extract_frames: Si True, extrait des images clés
            frame_interval: Intervalle en secondes entre les frames
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
            self.report_progress(0.1, "Analyse de la vidéo...")

            # Extraire les métadonnées vidéo
            video_meta = self._get_video_metadata(file_path)
            extra_metadata.update(video_meta)

            self.report_progress(0.2, "Copie du fichier...")

            # Copier dans le projet
            dest_path = self.copy_to_project(file_path, project_files_path)

            # Extraction et transcription audio si demandée
            if transcribe:
                self.report_progress(0.3, "Extraction de l'audio...")

                try:
                    audio_path = self._extract_audio(file_path, project_files_path)

                    self.report_progress(0.4, f"Chargement du modèle {whisper_model}...")

                    transcript_result = self._transcribe(
                        audio_path, whisper_model, language
                    )
                    content = transcript_result["text"]
                    extra_metadata["transcription"] = {
                        "model": whisper_model,
                        "language_detected": transcript_result.get("language"),
                        "segments": transcript_result.get("segments", []),
                    }

                    # Nettoyer le fichier audio temporaire
                    audio_path.unlink(missing_ok=True)

                    self.report_progress(0.8, "Transcription terminée")

                except ImportError as e:
                    warnings.append(str(e))
                except Exception as e:
                    warnings.append(f"Erreur de transcription: {e}")

            # Extraction des frames si demandée
            if extract_frames:
                self.report_progress(0.85, "Extraction des images...")

                try:
                    frames = self._extract_frames(
                        file_path, project_files_path, frame_interval
                    )
                    extra_metadata["extracted_frames"] = frames
                except Exception as e:
                    warnings.append(f"Erreur d'extraction des frames: {e}")

            self.report_progress(0.95, "Création de la source...")

            # Créer la source
            metadata = self.get_file_metadata(file_path)
            metadata.update(extra_metadata)

            source = Source(
                name=file_path.stem,
                type=SourceType.VIDEO,
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

    def _get_video_metadata(self, file_path: Path) -> dict:
        """Extrait les métadonnées d'une vidéo."""
        metadata = {}

        try:
            import cv2

            cap = cv2.VideoCapture(str(file_path))
            if cap.isOpened():
                metadata["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                metadata["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                metadata["fps"] = cap.get(cv2.CAP_PROP_FPS)
                metadata["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if metadata["fps"] > 0:
                    metadata["duration"] = metadata["frame_count"] / metadata["fps"]
                cap.release()

        except ImportError:
            pass

        # Essayer avec ffprobe
        if not metadata:
            try:
                import subprocess
                import json

                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_streams",
                        "-show_format",
                        str(file_path),
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for stream in data.get("streams", []):
                        if stream.get("codec_type") == "video":
                            metadata["width"] = stream.get("width")
                            metadata["height"] = stream.get("height")
                            metadata["fps"] = eval(stream.get("r_frame_rate", "0/1"))
                            metadata["codec"] = stream.get("codec_name")
                            break
                    if "format" in data:
                        metadata["duration"] = float(
                            data["format"].get("duration", 0)
                        )

            except Exception:
                pass

        return metadata

    def _extract_audio(self, video_path: Path, output_dir: Path) -> Path:
        """Extrait la piste audio d'une vidéo."""
        audio_path = output_dir / f"{video_path.stem}_audio.wav"

        try:
            # Essayer avec moviepy
            from moviepy.editor import VideoFileClip

            video = VideoFileClip(str(video_path))
            video.audio.write_audiofile(
                str(audio_path),
                verbose=False,
                logger=None,
            )
            video.close()
            return audio_path

        except ImportError:
            pass

        # Fallback avec ffmpeg
        try:
            import subprocess

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    str(audio_path),
                    "-y",
                ],
                capture_output=True,
            )
            if result.returncode == 0:
                return audio_path

        except FileNotFoundError:
            pass

        raise ImportError(
            "Installez moviepy ou ffmpeg pour extraire l'audio: "
            "pip install moviepy"
        )

    def _transcribe(
        self, audio_path: Path, model_name: str, language: Optional[str]
    ) -> dict:
        """Transcrit un fichier audio avec Whisper."""
        import whisper

        model = whisper.load_model(model_name)

        options = {}
        if language:
            options["language"] = language

        result = model.transcribe(str(audio_path), **options)

        # Simplifier les segments
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

    def _extract_frames(
        self, video_path: Path, output_dir: Path, interval: int
    ) -> list[str]:
        """Extrait des frames à intervalles réguliers."""
        frames_dir = output_dir / f"{video_path.stem}_frames"
        frames_dir.mkdir(exist_ok=True)
        frames = []

        try:
            import cv2

            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * interval)

            frame_count = 0
            saved_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    frame_path = frames_dir / f"frame_{saved_count:04d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    frames.append(str(frame_path))
                    saved_count += 1

                frame_count += 1

            cap.release()

        except ImportError:
            raise ImportError(
                "Installez opencv-python pour extraire les frames: "
                "pip install opencv-python"
            )

        return frames
