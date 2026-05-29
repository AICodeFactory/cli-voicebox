"""health subcommand."""

import argparse
import json

from loguru import logger

from cli_voicebox.client import VoiceboxClient, VoiceboxError
from cli_voicebox.config import load_config
from cli_voicebox.output import OutputFormat, api_result, emit_result
from cli_voicebox.user_paths import resolve_config_path


def health_command(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        logger.error(str(exc))
        return 1

    try:
        with VoiceboxClient(config) as client:
            health = client.get_health()
            root = client.get_root() if args.include_root else None
    except VoiceboxError as exc:
        logger.error(str(exc))
        emit_result(
            api_result("failed", msg=str(exc)),
            args.format,
            args.output,
        )
        return 1
    except Exception as exc:
        logger.error(str(exc))
        emit_result(api_result("failed", msg=str(exc)), args.format, args.output)
        return 1

    data: dict = {"health": health}
    if args.include_root:
        data["root"] = root

    emit_result(api_result("ok", data=data), args.format, args.output)
    return 0


def add_parser(
    subparsers: argparse._SubParsersAction,
    parents: list[argparse.ArgumentParser] | None = None,
) -> None:
    parser = subparsers.add_parser(
        "health",
        help="Check Voicebox server health (GET /health)",
        parents=parents or [],
    )
    parser.add_argument(
        "--include-root",
        action="store_true",
        help="Also call GET / (root endpoint)",
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
    parser.set_defaults(func=health_command)
