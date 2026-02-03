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
        show_timestamps: bool = False,
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
            show_timestamps: Si True, inclut les horodatages dans le texte
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

                    # Récupérer la durée pour l'estimation
                    video_duration = extra_metadata.get("duration")

                    self.report_progress(0.4, f"Chargement du modèle {whisper_model}...")

                    transcript_result = self._transcribe(
                        audio_path, whisper_model, language, video_duration
                    )
                    # Formater le contenu avec sauts de ligne entre segments
                    segments = transcript_result.get("segments", [])
                    content = self._format_transcript(segments, show_timestamps)
                    extra_metadata["transcription"] = {
                        "model": whisper_model,
                        "language_detected": transcript_result.get("language"),
                        "segments": segments,
                        "show_timestamps": show_timestamps,
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
                    frames = self._extract_frames(file_path, project_files_path, frame_interval)
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
                            # Parsing sécurisé du frame rate (évite eval())
                            fps_str = stream.get("r_frame_rate", "0/1")
                            try:
                                if "/" in fps_str:
                                    num, den = fps_str.split("/", 1)
                                    metadata["fps"] = int(num) / int(den) if int(den) != 0 else 0
                                else:
                                    metadata["fps"] = float(fps_str)
                            except (ValueError, ZeroDivisionError):
                                metadata["fps"] = 0
                            metadata["codec"] = stream.get("codec_name")
                            break
                    if "format" in data:
                        metadata["duration"] = float(data["format"].get("duration", 0))

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
            "Installez moviepy ou ffmpeg pour extraire l'audio: " "pip install moviepy"
        )

    def _transcribe(
        self,
        audio_path: Path,
        model_name: str,
        language: Optional[str],
        video_duration: Optional[float] = None,
    ) -> dict:
        """Transcrit un fichier audio avec Whisper."""
        import whisper
        from ..utils.system import get_whisper_device

        device = get_whisper_device()
        model = whisper.load_model(model_name, device=device)

        # Afficher l'estimation du temps
        estimated_time = self._estimate_transcription_time(video_duration, model_name, device)
        duration_str = self._format_duration(video_duration) if video_duration else ""
        estimate_str = self._format_duration(estimated_time) if estimated_time else ""

        if duration_str and estimate_str:
            progress_msg = f"Transcription en cours ({device}) - Vidéo: {duration_str}, estimé: ~{estimate_str}"
        elif duration_str:
            progress_msg = f"Transcription en cours ({device}) - Vidéo: {duration_str}"
        else:
            progress_msg = f"Transcription en cours ({device})..."

        self.report_progress(0.5, progress_msg)

        options = {}
        if language:
            options["language"] = language

        # Activer FP16 sur GPU
        if device == "cuda":
            options["fp16"] = True
        else:
            options["fp16"] = False

        result = model.transcribe(str(audio_path), **options)

        # Simplifier les segments
        simplified_segments = []
        for seg in result.get("segments", []):
            simplified_segments.append(
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                }
            )

        return {
            "text": result["text"].strip(),
            "language": result.get("language"),
            "segments": simplified_segments,
        }

    def _format_transcript(self, segments: list[dict], show_timestamps: bool = False) -> str:
        """
        Formate la transcription avec sauts de ligne entre segments.

        Args:
            segments: Liste des segments avec start, end, text
            show_timestamps: Si True, inclut les horodatages

        Returns:
            Texte formaté avec sauts de ligne
        """
        if not segments:
            return ""

        lines = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            if show_timestamps:
                start = self._format_timestamp(seg["start"])
                end = self._format_timestamp(seg["end"])
                lines.append(f"[{start} -> {end}] {text}")
            else:
                lines.append(text)

        return "\n\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Formate un timestamp en HH:MM:SS ou MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_duration(seconds: Optional[float]) -> str:
        """Formate une durée en format lisible (ex: '5 min 30 s')."""
        if seconds is None or seconds <= 0:
            return ""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h {minutes:02d}min"
        elif minutes > 0:
            return f"{minutes} min {secs:02d}s"
        else:
            return f"{secs}s"

    @staticmethod
    def _estimate_transcription_time(
        video_duration: Optional[float],
        model_name: str,
        device: str,
    ) -> Optional[float]:
        """
        Estime le temps de transcription basé sur la durée vidéo, le modèle et le device.
        """
        if video_duration is None or video_duration <= 0:
            return None

        # Facteurs de vitesse approximatifs
        speed_factors = {
            "cuda": {
                "tiny": 0.05,
                "base": 0.08,
                "small": 0.15,
                "medium": 0.3,
                "large": 0.6,
            },
            "cpu": {
                "tiny": 0.3,
                "base": 0.5,
                "small": 1.0,
                "medium": 2.5,
                "large": 6.0,
            },
        }

        device_key = "cuda" if device == "cuda" else "cpu"
        model_key = model_name.lower().replace("-", "").replace(".", "")
        factors = speed_factors.get(device_key, speed_factors["cpu"])
        factor = factors.get(model_key, factors.get("medium", 1.0))

        estimated = video_duration * factor

        # Overhead pour chargement + extraction audio
        overhead = {"tiny": 10, "base": 15, "small": 25, "medium": 40, "large": 60}
        estimated += overhead.get(model_key, 30)

        return estimated

    def _extract_frames(self, video_path: Path, output_dir: Path, interval: int) -> list[str]:
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
                "Installez opencv-python pour extraire les frames: " "pip install opencv-python"
            )

        return frames
