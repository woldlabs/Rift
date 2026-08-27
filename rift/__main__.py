"""CLI entry for Rift.

Usage:
    python -m rift              # launch the map UI
    python -m rift serve
    python -m rift version
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="rift",
        description="RIFT — Reality Integrity & Fracture Tracker",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="Launch the map UI")
    sub.add_parser("gui", help="Alias for serve")
    sub.add_parser("version", help="Print version")

    if not argv:
        from rift.web.app import main as serve
        serve()
        return 0

    args = parser.parse_args(argv)
    if args.command in {"serve", "gui"}:
        from rift.web.app import main as serve
        serve()
        return 0
    if args.command == "version":
        from rift import __version__
        print(f"rift {__version__}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
