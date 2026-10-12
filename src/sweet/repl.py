from __future__ import annotations

import re
import sys

from .compiler import Session
from .diagnostics.errors import SweetError

HELP = """Anne REPL. End statements with ';'.
  data sales = read "sales.csv";     sales.filter(price > 10).show();
  :datasets   list bound datasets    :reset   forget everything    :quit   leave"""


def _complete(buf: str) -> bool:
    last = [ln for ln in buf.splitlines() if ln.strip()][-1]
    return re.sub(r"#.*$", "", last).rstrip().endswith(";")


def run(session=None, output_dir="sweet_output", input_fn=input, out=None) -> int:
    out = out if out is not None else sys.stdout
    try:
        import readline  # noqa: F401  (line editing/history where available)
    except ImportError:
        pass
    make = lambda: Session(base_dir=".", output_dir=output_dir, out=out)
    session = session or make()
    print("Anne REPL (sweet). :help for help.", file=out)
    buf = ""
    while True:
        try:
            line = input_fn("anne> " if not buf else "...> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            buf = ""
            print(file=out)
            continue
        text = line.strip()
        if not buf and text.startswith(":"):
            cmd = text.split()[0]
            if cmd in (":q", ":quit", ":exit"):
                break
            if cmd == ":help":
                print(HELP, file=out)
            elif cmd == ":reset":
                session = make()
                print("session reset", file=out)
            elif cmd == ":datasets":
                for name in session.compiler.analyzer.symbols.names():
                    obj = session.dataset(name)
                    ds = getattr(obj, "dataset", obj)
                    print(f"{name}: [{', '.join(ds.columns)}]", file=out)
            else:
                print(f"unknown command {cmd}; try :help", file=out)
            continue
        if not buf and not text:
            continue
        buf += line + "\n"
        if not _complete(buf):
            continue
        try:
            session.run(buf)
        except SweetError as e:
            print(e.render(buf, "<repl>"), file=sys.stderr)
        buf = ""
    return 0
