"""Tier 1 suites (IMPLEMENTATION_PLAN §5). Each suite folder holds `suite.yaml` (tasks, upstream arms, metrics,
credits); this module turns it into cells and runs them with the upstream's own instrument.

A suite module exposes: METRICS {name: lower_is_better}, cells(cfg) -> [cell], run_cell(cell, ctx) -> record with
`metrics`. Upstream clones are read from $AGYLITE_UPSTREAMS_DIR (default ~/Developer/os), never edited.
"""
import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


def upstreams_dir() -> Path:
    return Path(os.environ.get("AGYLITE_UPSTREAMS_DIR") or Path.home() / "Developer" / "os")


def load_suite(name: str) -> dict:
    path = HERE / name / "suite.yaml"
    if not path.is_file():
        raise KeyError(f"unknown suite {name}; known: {', '.join(names())}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def names():
    return sorted(p.parent.name for p in HERE.glob("*/suite.yaml"))


def module(cfg: dict):
    import importlib
    return importlib.import_module(f"{__name__}.{cfg['runner']}")
