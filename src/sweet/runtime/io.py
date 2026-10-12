"""File readers/writers. Everything goes straight into Polars; Pandas is never used."""
from __future__ import annotations

from pathlib import Path

import polars as pl

from ..diagnostics.errors import SweetRuntimeError, SweetSemanticError
from ..semantic.types import from_polars

READ_FORMATS = {
    ".csv": "csv", ".tsv": "csv", ".parquet": "parquet", ".json": "json",
    ".ndjson": "ndjson", ".jsonl": "ndjson", ".xlsx": "excel",
}
WRITE_FORMATS = {".csv": "csv", ".parquet": "parquet", ".json": "json", ".ndjson": "ndjson", ".jsonl": "ndjson"}
OPTION_SPECS = {
    "csv": {"header": bool, "infer_schema": bool, "delimiter": str},
    "excel": {"header": bool, "sheet": str},
    "json": {}, "ndjson": {}, "parquet": {},
}


def format_of(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext not in READ_FORMATS:
        raise SweetSemanticError(f"cannot read '{path}': unsupported file type '{ext or '(none)'}'",
                                 hint="supported: " + ", ".join(sorted(READ_FORMATS)))
    return READ_FORMATS[ext]


def validate_options(fmt: str, options: dict) -> None:
    spec = OPTION_SPECS[fmt]
    for name, value in options.items():
        if name not in spec:
            allowed = ", ".join(spec) if spec else "none"
            raise SweetSemanticError(f"option '{name}' is not supported for {fmt} files",
                                     hint=f"supported options: {allowed}")
        want = spec[name]
        if type(value) is not want:
            raise SweetSemanticError(f"option '{name}' must be a {want.__name__}")
        if name == "delimiter" and len(value) != 1:
            raise SweetSemanticError("option 'delimiter' must be a single character")


def resolve(path: str, base_dir) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path(base_dir) / p
    if not p.is_file():
        raise SweetSemanticError(f"file not found: '{path}'", hint=f"looked in {p.parent}")
    return p


def scan(path: str, options=()) -> pl.LazyFrame:
    opts = dict(options)
    fmt = format_of(path)
    try:
        if fmt == "csv":
            kwargs = {
                "has_header": opts.get("header", True),
                "separator": opts.get("delimiter", "\t" if path.lower().endswith(".tsv") else ","),
            }
            if not opts.get("infer_schema", True):
                kwargs["infer_schema_length"] = 0  # every column is read as text
            return pl.scan_csv(path, **kwargs)
        if fmt == "parquet":
            return pl.scan_parquet(path)
        if fmt == "ndjson":
            return pl.scan_ndjson(path)
        if fmt == "json":
            return pl.read_json(path).lazy()
        if fmt == "excel":
            kwargs = {"has_header": opts.get("header", True)}
            if "sheet" in opts:
                kwargs["sheet_name"] = opts["sheet"]
            return pl.read_excel(path, **kwargs).lazy()
    except (pl.exceptions.PolarsError, OSError, ImportError, ValueError) as e:
        raise SweetRuntimeError(f"cannot read '{Path(path).name}': {e}") from None
    raise AssertionError(fmt)


def schema_of(path: str, options=()) -> tuple:
    try:
        schema = scan(path, options).collect_schema()
    except pl.exceptions.PolarsError as e:
        raise SweetRuntimeError(f"cannot read '{Path(path).name}': {e}") from None
    return tuple((name, from_polars(dtype)) for name, dtype in schema.items())


def write(df: pl.DataFrame, target: Path, fmt: str) -> None:
    if fmt == "csv":
        df.write_csv(target)
    elif fmt == "parquet":
        df.write_parquet(target)
    elif fmt == "ndjson":
        df.write_ndjson(target)
    elif fmt == "json":
        df.write_json(target)
    else:
        raise AssertionError(fmt)
