"""CLI entry point for cli-voicebox."""

import argparse
import sys

from loguru import logger

from cli_voicebox import help_text
from cli_voicebox.commands import audio as audio_cmd
from cli_voicebox.commands import generate as generate_cmd
from cli_voicebox.commands import health as health_cmd
from cli_voicebox.commands import history as history_cmd
from cli_voicebox.commands import init_cmd
from cli_voicebox.commands import models as models_cmd
from cli_voicebox.commands import profiles as profiles_cmd
from cli_voicebox.user_paths import (
    ensure_user_config_if_missing,
    get_default_config_path,
)


def _build_parent_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    default_cfg = str(get_default_config_path())
    parent.add_argument(
        "-c",
        "--config",
        default=None,
        metavar="FILE",
        help=(
            f"JSON config path. Default (omit -c): user config at {default_cfg} "
            "(auto-created; platform paths in --help)"
        ),
    )
    parent.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logs to stderr (stdout stays JSON only)",
    )
    return parent


def _argv_requests_help(argv: list[str] | None) -> bool:
    args = argv if argv is not None else sys.argv[1:]
    return "-h" in args or "--help" in args


def main(argv: list[str] | None = None) -> int:
    if _argv_requests_help(argv):
        created = ensure_user_config_if_missing()
        if created:
            print(
                f"Created default config: {get_default_config_path()}",
                file=sys.stderr,
            )

    parent = _build_parent_parser()
    parser = argparse.ArgumentParser(
        prog="voicebox-cli",
        description=help_text.MAIN_DESCRIPTION,
        epilog=help_text.build_main_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parent],
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="subcommands",
        metavar="COMMAND",
        description=(
            "init | health | profiles | generate | audio | history | models "
            "— use: voicebox-cli COMMAND --help"
        ),
    )
    init_cmd.add_parser(subparsers, parents=[parent])
    health_cmd.add_parser(subparsers, parents=[parent])
    profiles_cmd.add_parser(subparsers, parents=[parent])
    generate_cmd.add_parser(subparsers, parents=[parent])
    audio_cmd.add_parser(subparsers, parents=[parent])
    history_cmd.add_parser(subparsers, parents=[parent])
    models_cmd.add_parser(subparsers, parents=[parent])

    args = parser.parse_args(argv)

    logger.remove()
    level = "DEBUG" if args.verbose else "INFO"
    logger.add(sys.stderr, level=level)

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
