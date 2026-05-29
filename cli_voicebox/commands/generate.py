"""generate subcommand."""

import argparse
import json
from pathlib import Path
from typing import Any

from loguru import logger

from cli_voicebox import help_text
from cli_voicebox.client import VoiceboxClient, VoiceboxError
from cli_voicebox.config import load_config
from cli_voicebox.output import api_result, emit_result
from cli_voicebox.user_paths import resolve_config_path


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Body file must contain a JSON object")
        return data

    if not args.text:
        raise ValueError("Either -t/--text or --body-file is required")
    if not args.profile_id:
        raise ValueError("--profile-id is required (see: voicebox-cli profiles)")

    payload: dict[str, Any] = {
        "text": args.text,
        "profile_id": args.profile_id,
    }
    if args.language:
        payload["language"] = args.language
    if args.engine:
        payload["engine"] = args.engine
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.model_size:
        payload["model_size"] = args.model_size
    if args.instruct:
        payload["instruct"] = args.instruct
    if args.max_chunk_chars is not None:
        payload["max_chunk_chars"] = args.max_chunk_chars
    return payload


def _save_audio(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _resolve_generation_id(meta: dict[str, Any]) -> str | None:
    for key in ("id", "generation_id"):
        value = meta.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def generate_command(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    try:
        config = load_config(config_path)
        payload = _build_payload(args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        logger.error(str(exc))
        return 1

    audio_path: str | None = None
    try:
        with VoiceboxClient(config) as client:
            meta, raw_audio = client.generate(payload)

            if args.audio_out:
                out = Path(args.audio_out)
                if raw_audio:
                    _save_audio(out, raw_audio)
                    audio_path = str(out.resolve())
                elif meta:
                    gen_id = _resolve_generation_id(meta)
                    if not gen_id:
                        raise VoiceboxError(
                            "No generation id in response; cannot download audio"
                        )
                    audio_bytes = client.download_audio(gen_id)
                    _save_audio(out, audio_bytes)
                    audio_path = str(out.resolve())
                else:
                    raise VoiceboxError("Empty response from /generate")
    except VoiceboxError as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1
    except Exception as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1

    result = api_result("ok", data=meta, audio_file=audio_path)
    emit_result(result, args.format, args.output)
    return 0


def add_parser(
    subparsers: argparse._SubParsersAction,
    parents: list[argparse.ArgumentParser] | None = None,
) -> None:
    parser = subparsers.add_parser(
        "generate",
        help=help_text.SUBCOMMAND_SUMMARY["generate"],
        description=help_text.GENERATE_DESCRIPTION,
        epilog=help_text.GENERATE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents or [],
    )
    parser.add_argument(
        "-t",
        "--text",
        default=None,
        metavar="TEXT",
        help="Text to synthesize",
    )
    parser.add_argument(
        "--profile-id",
        default=None,
        metavar="ID",
        help="Voice profile UUID (from: voicebox-cli profiles)",
    )
    parser.add_argument(
        "--language",
        default=None,
        metavar="CODE",
        help="Language code, e.g. en, zh",
    )
    parser.add_argument(
        "--engine",
        default=None,
        metavar="NAME",
        help="TTS engine: qwen, luxtts, kokoro, chatterbox, ...",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
    )
    parser.add_argument(
        "--model-size",
        default=None,
        metavar="SIZE",
        help='Model size, e.g. "1.7B"',
    )
    parser.add_argument(
        "--instruct",
        default=None,
        metavar="TEXT",
        help="Delivery style instruct (qwen_custom_voice)",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=None,
        metavar="N",
        help="Long-text chunk size (100-5000)",
    )
    parser.add_argument(
        "--body-file",
        default=None,
        metavar="FILE",
        help="Full POST /generate JSON body (overrides -t and flags)",
    )
    parser.add_argument(
        "-o",
        "--audio-out",
        default=None,
        metavar="FILE",
        help="Save generated audio (WAV) to FILE",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write response JSON metadata to FILE (stdout if omitted)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )
    parser.set_defaults(func=generate_command)
