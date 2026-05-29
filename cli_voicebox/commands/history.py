"""history subcommand."""

import argparse
import json

from loguru import logger

from cli_voicebox.client import VoiceboxClient, VoiceboxError
from cli_voicebox.config import load_config
from cli_voicebox.output import api_result, emit_result
from cli_voicebox.user_paths import resolve_config_path


def history_command(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        logger.error(str(exc))
        return 1

    try:
        with VoiceboxClient(config) as client:
            history = client.list_history(limit=args.limit)
    except VoiceboxError as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1
    except Exception as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1

    emit_result(api_result("ok", data=history), args.format, args.output)
    return 0


def add_parser(
    subparsers: argparse._SubParsersAction,
    parents: list[argparse.ArgumentParser] | None = None,
) -> None:
    parser = subparsers.add_parser(
        "history",
        help="List generation history (GET /history)",
        parents=parents or [],
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max items (if supported by server)",
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
    parser.set_defaults(func=history_command)
