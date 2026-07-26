#!/usr/bin/env python3
"""Onairos connect/sync entrypoint for Hermes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onairos_skill import (
    MAX_PERSONA_CHARS,
    MAX_RESPONSE_BYTES,
    MAX_SUMMARY_CHARS,
    build_ssl_context as _build_ssl_context,
    connect,
    default_urlopen as _default_urlopen,
    format_persona,
    state_path,
    sync,
)


__all__ = (
    "MAX_PERSONA_CHARS",
    "MAX_RESPONSE_BYTES",
    "MAX_SUMMARY_CHARS",
    "_build_ssl_context",
    "_default_urlopen",
    "connect",
    "format_persona",
    "main",
    "state_path",
    "sync",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Connect an Onairos profile to Hermes.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("connect", "sync"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--session-key", required=True)
        subparser.add_argument("--state-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    kwargs = {"state_dir": args.state_dir} if args.state_dir is not None else {}
    operation = connect if args.command == "connect" else sync
    result = operation(args.session_key, **kwargs)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
