#!/usr/bin/env python3
"""Measure exporter runtime phases for one project database."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id", type=int)
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "backend",
    )
    parser.add_argument(
        "--projects-db-path",
        type=Path,
        help="Override the project database root, useful for benchmarking copied DBs.",
    )
    parser.add_argument(
        "--recalculate",
        type=parse_bool,
        default=True,
        help="Whether to force a full recompute. Defaults to true.",
    )
    parser.add_argument(
        "--payload-format",
        choices=("compact", "expanded"),
        default="compact",
        help="Response payload format to benchmark. Defaults to compact.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write the benchmark result JSON.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend_dir))
    os.environ.setdefault("SECRET_KEY", "benchmark-secret-key")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.dev")

    import django

    django.setup()

    from src.exporter.benchmark_runtime import run_export_benchmark

    result = run_export_benchmark(
        args.project_id,
        recalculate=args.recalculate,
        payload_format=args.payload_format,
        projects_db_path=args.projects_db_path,
    )
    output = result.to_dict()
    json_output = json.dumps(output, indent=2)
    print(json_output)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json_output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
