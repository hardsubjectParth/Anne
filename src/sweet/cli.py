from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .compiler import Session
from .diagnostics.errors import SweetError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sweet", description="Sweet: compiler and runner for Anne dataset programs")
    ap.add_argument("file", nargs="?", help="an .anne program (omit to start the REPL)")
    ap.add_argument("-o", "--output", help="directory for explicit save() exports (default: ./<program name>/)")
    ap.add_argument("--check", action="store_true", help="parse and type-check only; do not execute")
    ap.add_argument("--version", action="version", version=f"sweet {__version__}")
    args = ap.parse_args(argv)

    if args.file is None:
        from .repl import run

        return run(output_dir=args.output or "sweet_output")

    path = Path(args.file)
    if not path.is_file():
        print(f"error: cannot find '{args.file}'", file=sys.stderr)
        return 2
    source = path.read_text(encoding="utf-8")
    session = Session(base_dir=path.resolve().parent, output_dir=args.output or path.stem)
    try:
        session.run(source, execute=not args.check)
    except SweetError as e:
        sys.stdout.flush()
        print(e.render(source, str(path)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
