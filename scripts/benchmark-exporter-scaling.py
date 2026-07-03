#!/usr/bin/env python3
"""Benchmark exporter runtime across a deterministic changed-session sweep."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_sizes(value: str) -> list[int]:
    sizes = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        sizes.append(int(chunk))
    if not sizes:
        raise argparse.ArgumentTypeError("At least one benchmark size is required.")
    return sizes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--project-id", type=int, help="Seed project id under the projects DB root.")
    target.add_argument(
        "--project-db-dir",
        type=Path,
        help="Path to a project database directory containing initial/general DB files.",
    )
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "backend",
    )
    parser.add_argument(
        "--projects-db-path",
        type=Path,
        help="Override the source projects DB root when using --project-id.",
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=parse_sizes("0,5,10,20,40,80,160"),
        help="Comma-separated changed-session sizes to benchmark.",
    )
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260702)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "tmp" / "exporter-benchmarks",
    )
    parser.add_argument(
        "--payload-format",
        choices=("compact", "expanded"),
        default="compact",
    )
    parser.add_argument(
        "--recalculate",
        choices=("true", "false"),
        default="true",
    )
    parser.add_argument(
        "--keep-temp-dbs",
        action="store_true",
        help="Keep copied project DB directories under the output directory for inspection.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend_dir))
    os.environ.setdefault("SECRET_KEY", "benchmark-secret-key")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.dev")

    import django

    django.setup()

    from django.conf import settings

    from src.exporter.benchmark_runtime import run_export_benchmark
    from src.exporter.benchmark_scaling import (
        DEFAULT_BENCHMARK_SEED,
        ScalingRunRecord,
        build_scaling_artifact,
        build_size_summary,
        cleanup_project_tree,
        copy_project_tree,
        ensure_clean_exporter_baseline,
        ensure_clean_exporter_baseline_paths,
        mutate_project_for_benchmark,
        print_growth_diagnostics,
        print_size_summary,
        write_scaling_artifacts,
    )

    project_id = args.project_id if args.project_id is not None else 1
    source_projects_root = Path(args.projects_db_path) if args.projects_db_path else Path(settings.PROJECTS_DB_PATH)
    source_project_dir = (
        source_projects_root / str(project_id)
        if args.project_id is not None
        else args.project_db_dir.resolve()
    )
    if not source_project_dir.exists():
        raise SystemExit(f"Project database directory not found: {source_project_dir}")

    source_label = (
        f"project_id:{project_id}"
        if args.project_id is not None
        else f"project_dir:{source_project_dir}"
    )
    recalculate = args.recalculate == "true"
    seed = args.seed if args.seed is not None else DEFAULT_BENCHMARK_SEED

    if args.project_id is not None:
        ensure_clean_exporter_baseline(project_id, projects_db_path=source_project_dir.parent)
    else:
        ensure_clean_exporter_baseline_paths(
            source_project_dir / "general_database.db",
            source_project_dir / "initial_database.db",
        )

    records: list[ScalingRunRecord] = []
    previous_summary = None
    for size in args.sizes:
        size_records: list[ScalingRunRecord] = []
        for run_number in range(1, args.repetitions + 1):
            tempdir: tempfile.TemporaryDirectory[str] | None = None
            if args.keep_temp_dbs:
                temp_projects_root = args.output_dir / "temp-dbs" / f"size-{size}" / f"run-{run_number}"
                temp_projects_root.mkdir(parents=True, exist_ok=True)
            else:
                tempdir = tempfile.TemporaryDirectory(prefix=f"exporter-scale-{size}-")
                temp_projects_root = Path(tempdir.name)

            copied_project_dir = copy_project_tree(source_project_dir, temp_projects_root, project_id)
            try:
                mutation = mutate_project_for_benchmark(
                    project_id,
                    changed_sessions=size,
                    seed=seed,
                    projects_db_path=temp_projects_root,
                )
                benchmark = run_export_benchmark(
                    project_id,
                    recalculate=recalculate,
                    payload_format=args.payload_format,
                    projects_db_path=temp_projects_root,
                )
                record = ScalingRunRecord(
                    requested_changed_sessions=size,
                    actual_changed_sessions=mutation.actual_changed_sessions,
                    run_number=run_number,
                    mutation=mutation,
                    benchmark=benchmark,
                )
                size_records.append(record)
                records.append(record)
            finally:
                if not args.keep_temp_dbs:
                    cleanup_project_tree(copied_project_dir)
                    assert tempdir is not None
                    tempdir.cleanup()

        summary = build_size_summary(size, size_records, previous_summary)
        print_size_summary(summary)
        previous_summary = summary

    git_commit_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    git_commit = git_commit_result.stdout.strip() if git_commit_result.returncode == 0 else None

    artifact = build_scaling_artifact(
        source_project=source_label,
        source_project_dir=source_project_dir,
        sizes=args.sizes,
        repetitions=args.repetitions,
        seed=seed,
        recalculate=recalculate,
        payload_format=args.payload_format,
        records=records,
        git_commit=git_commit,
    )
    print_growth_diagnostics(artifact)
    json_path, csv_path = write_scaling_artifacts(artifact, args.output_dir)
    print(f"json_report={json_path}")
    print(f"csv_summary={csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
