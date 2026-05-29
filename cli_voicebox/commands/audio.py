"""audio subcommand."""

import argparse
import json
from pathlib import Path

from loguru import logger

from cli_voicebox.client import VoiceboxClient, VoiceboxError
from cli_voicebox.config import load_config
from cli_voicebox.output import api_result, emit_result
from cli_voicebox.user_paths import resolve_config_path


def audio_command(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        logger.error(str(exc))
        return 1

    if not args.generation_id:
        logger.error("--generation-id is required")
        return 1
    if not args.output and not args.audio_out:
        logger.error("Specify -o/--output (JSON) and/or --audio-out FILE for WAV")
        return 1

    audio_path: str | None = None
    try:
        with VoiceboxClient(config) as client:
            audio_bytes = client.download_audio(args.generation_id)
            if args.audio_out:
                out = Path(args.audio_out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(audio_bytes)
                audio_path = str(out.resolve())
    except VoiceboxError as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1
    except Exception as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1

    data = {"generation_id": args.generation_id, "bytes": len(audio_bytes)}
    result = api_result("ok", data=data, audio_file=audio_path)

    if args.output or not args.audio_out:
        emit_result(result, args.format, args.output)
    elif args.audio_out:
        # Only saving audio: minimal JSON to stdout unless --format text
        emit_result(result, args.format, None)

    return 0


def add_parser(
    subparsers: argparse._SubParsersAction,
    parents: list[argparse.ArgumentParser] | None = None,
) -> None:
    parser = subparsers.add_parser(
        "audio",
        help="Download audio by generation id (GET /audio/{id})",
        parents=parents or [],
    )
    parser.add_argument(
        "--generation-id",
        required=True,
        metavar="ID",
        help="Generation UUID from generate response data.id",
    )
    parser.add_argument(
        "--audio-out",
        default=None,
        metavar="FILE",
        help="Save WAV/audio bytes to FILE",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="FILE",
        help="Write response JSON to FILE",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )
    parser.set_defaults(func=audio_command)
