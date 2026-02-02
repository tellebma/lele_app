"""Importer pour les fichiers audio avec transcription."""

from pathlib import Path
from typing import Optional
import traceback

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType
from .. import get_logger
from ..utils.ffmpeg import setup_ffmpeg, check_ffmpeg
from ..utils.system import get_whisper_device, get_model_recommendations, get_system_info

# Logger pour ce module
logger = get_logger("importers.audio")


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

        logger.info(f"=== Début import audio: {file_path.name} ===")
        logger.info(f"Paramètres: transcribe={transcribe}, model={whisper_model}, lang={language}")

        valid, error = self.validate_file(file_path)
        if not valid:
            logger.error(f"Validation échouée: {error}")
            return ImportResult(success=False, error=error)

        warnings = []
        content = ""
        extra_metadata = {}

        try:
            self.report_progress(0.1, "Analyse du fichier audio...")
            logger.info("Extraction des métadonnées audio...")

            # Extraire les métadonnées audio
            audio_meta = self._get_audio_metadata(file_path)
            extra_metadata.update(audio_meta)
            logger.info(f"Métadonnées extraites: durée={audio_meta.get('duration')}s")

            self.report_progress(0.2, "Copie du fichier...")
            logger.info(f"Copie vers: {project_files_path}")

            # Copier dans le projet
            dest_path = self.copy_to_project(file_path, project_files_path)
            logger.info(f"Fichier copié: {dest_path}")

            # Transcription si demandée
            if transcribe:
                logger.info(f"=== Début transcription avec modèle {whisper_model} ===")
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
                    logger.info(f"Transcription réussie: {len(content)} caractères")
                    logger.info(f"Langue détectée: {transcript_result.get('language')}")
                    logger.info(f"Nombre de segments: {len(transcript_result.get('segments', []))}")
                    self.report_progress(0.9, "Transcription terminée")

                except ImportError as e:
                    warning_msg = "Whisper non installé. Installez-le avec: pip install openai-whisper"
                    warnings.append(warning_msg)
                    logger.error(f"ImportError: {warning_msg}")
                    logger.debug(traceback.format_exc())

                except Exception as e:
                    warning_msg = f"Erreur de transcription: {e}"
                    warnings.append(warning_msg)
                    logger.error(f"Exception transcription: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.info("Transcription désactivée par l'utilisateur")

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

            logger.info(f"Source créée: name={source.name}, content_length={len(content)}")
            self.report_progress(1.0, "Import terminé")

            if warnings:
                logger.warning(f"Import terminé avec {len(warnings)} avertissement(s)")
                for w in warnings:
                    logger.warning(f"  - {w}")

            logger.info(f"=== Fin import audio: {file_path.name} - SUCCÈS ===")

            return ImportResult(
                success=True,
                source=source,
                warnings=warnings,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"=== Fin import audio: {file_path.name} - ÉCHEC ===")
            logger.error(f"Exception: {e}")
            logger.error(traceback.format_exc())
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

                logger.debug(f"Métadonnées mutagen: {metadata}")

        except ImportError:
            logger.warning("mutagen non installé - métadonnées audio limitées")
        except Exception as e:
            logger.warning(f"Erreur extraction métadonnées: {e}")

        return metadata

    def _transcribe(
        self, file_path: Path, model_name: str, language: Optional[str]
    ) -> dict:
        """Transcrit un fichier audio avec Whisper."""
        # Configurer FFmpeg avant d'utiliser Whisper
        logger.info("Configuration de FFmpeg...")
        ffmpeg_info = check_ffmpeg()
        if not ffmpeg_info["available"]:
            raise RuntimeError(
                "FFmpeg n'est pas disponible. "
                "Installez-le avec: pip install imageio-ffmpeg"
            )
        logger.info(f"FFmpeg disponible: {ffmpeg_info['source']} - {ffmpeg_info['path']}")

        # Ajouter FFmpeg au PATH pour Whisper
        if not setup_ffmpeg():
            raise RuntimeError("Impossible de configurer FFmpeg")

        # Détecter le matériel disponible
        logger.info("=== Détection du matériel ===")
        device = get_whisper_device()
        system_info = get_system_info()

        if system_info.torch_cuda_available:
            logger.info(f"✅ GPU CUDA disponible: {system_info.gpus[0].name if system_info.gpus else 'Unknown'}")
            logger.info(f"   CUDA version: {system_info.torch_cuda_version}")
            if system_info.gpus:
                gpu = system_info.gpus[0]
                logger.info(f"   Mémoire GPU: {gpu.memory_free_mb} / {gpu.memory_total_mb} MB")
        else:
            logger.info("❌ GPU CUDA non disponible - utilisation du CPU")
            if system_info.has_nvidia_gpu:
                logger.warning(
                    "GPU NVIDIA détecté mais PyTorch n'a pas CUDA. "
                    "Installez PyTorch avec CUDA pour accélérer la transcription."
                )

        # Vérifier les recommandations pour ce modèle
        recommendations = get_model_recommendations(model_name)
        for warning in recommendations["warnings"]:
            logger.warning(warning)

        logger.info(f"Device sélectionné: {device.upper()}")

        logger.info("Import du module whisper...")
        import whisper

        logger.info(f"Chargement du modèle '{model_name}' sur {device}...")
        logger.info("(Cela peut prendre du temps si le modèle doit être téléchargé)")
        self.report_progress(0.4, f"Chargement du modèle {model_name} ({device})...")

        # Charger le modèle sur le device approprié
        model = whisper.load_model(model_name, device=device)
        logger.info(f"Modèle '{model_name}' chargé avec succès sur {device}")

        logger.info(f"Début de la transcription de: {file_path}")
        self.report_progress(0.5, f"Transcription en cours ({device})...")

        options = {}
        if language:
            options["language"] = language
            logger.info(f"Langue forcée: {language}")
        else:
            logger.info("Détection automatique de la langue")

        # Activer FP16 sur GPU pour plus de performance
        if device == "cuda":
            options["fp16"] = True
            logger.info("FP16 activé pour GPU")
        else:
            options["fp16"] = False

        logger.info("Appel de model.transcribe()...")
        result = model.transcribe(str(file_path), **options)
        logger.info("Transcription terminée")

        # Simplifier les segments pour le stockage
        simplified_segments = []
        for seg in result.get("segments", []):
            simplified_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            })

        text = result["text"].strip()
        logger.info(f"Résultat: {len(text)} caractères, {len(simplified_segments)} segments")

        return {
            "text": text,
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
