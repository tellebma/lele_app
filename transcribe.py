#!/usr/bin/env python3
"""
Script de transcription audio utilisant Whisper d'OpenAI.

Usage:
    python transcribe.py <fichier_audio> [--model MODEL] [--language LANG] [--output OUTPUT]

Exemples:
    python transcribe.py audio.mp3
    python transcribe.py audio.wav --model medium --language fr
    python transcribe.py audio.mp3 --output transcript.txt
"""

import argparse
import sys
from pathlib import Path

import whisper


def transcribe_audio(
    audio_path: str,
    model_name: str = "base",
    language: str | None = None,
) -> dict:
    """
    Transcrit un fichier audio en texte.

    Args:
        audio_path: Chemin vers le fichier audio
        model_name: Nom du modèle Whisper (tiny, base, small, medium, large)
        language: Code de langue (ex: 'fr', 'en'). None pour détection auto.

    Returns:
        Dictionnaire contenant la transcription et les métadonnées
    """
    print(f"Chargement du modèle '{model_name}'...")
    model = whisper.load_model(model_name)

    print(f"Transcription de '{audio_path}'...")
    options = {}
    if language:
        options["language"] = language

    result = model.transcribe(audio_path, **options)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Transcrit un fichier audio en texte",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modèles disponibles:
  tiny    - Le plus rapide, moins précis (~1GB VRAM)
  base    - Bon compromis vitesse/qualité (~1GB VRAM)
  small   - Meilleure qualité (~2GB VRAM)
  medium  - Haute qualité (~5GB VRAM)
  large   - Meilleure qualité (~10GB VRAM)

Exemples:
  python transcribe.py audio.mp3
  python transcribe.py audio.wav --model medium --language fr
  python transcribe.py audio.mp3 --output transcript.txt
        """,
    )

    parser.add_argument("audio_file", help="Chemin vers le fichier audio à transcrire")
    parser.add_argument(
        "--model",
        "-m",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Modèle Whisper à utiliser (défaut: base)",
    )
    parser.add_argument(
        "--language",
        "-l",
        default=None,
        help="Code de langue (ex: 'fr', 'en'). Détection auto si non spécifié",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Fichier de sortie pour la transcription (défaut: affichage console)",
    )

    args = parser.parse_args()

    # Vérifier que le fichier existe
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Erreur: Le fichier '{args.audio_file}' n'existe pas.", file=sys.stderr)
        sys.exit(1)

    # Vérifier l'extension
    valid_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}
    if audio_path.suffix.lower() not in valid_extensions:
        print(
            f"Attention: Extension '{audio_path.suffix}' non standard. "
            f"Extensions supportées: {', '.join(valid_extensions)}",
            file=sys.stderr,
        )

    # Transcrire
    result = transcribe_audio(
        str(audio_path),
        model_name=args.model,
        language=args.language,
    )

    transcript = result["text"].strip()
    detected_language = result.get("language", "inconnu")

    print(f"\nLangue détectée: {detected_language}")
    print("-" * 50)

    # Sortie
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(transcript, encoding="utf-8")
        print(f"Transcription sauvegardée dans '{args.output}'")
        print(f"\nAperçu:\n{transcript[:500]}{'...' if len(transcript) > 500 else ''}")
    else:
        print(f"\nTranscription:\n{transcript}")


if __name__ == "__main__":
    main()
