"""Run the mortality graph with explicit inputs and output placement."""

import argparse
from pathlib import Path

from . import run_mortality_graph
from .synthetic import write_synthetic_inputs


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument("--synthetic", action="store_true")
    for name in ("training", "rates", "initial", "holdout"):
        result.add_argument(f"--{name}", type=Path)
    result.add_argument("--boundary-year", type=int, default=2014)
    result.add_argument("--external-vintage-year", type=int, default=2014)
    result.add_argument("--experiment-id", default="mortality")
    result.add_argument("--replicate", type=int, default=0)
    result.add_argument("--base-seed", type=int, default=0)
    return result


def main(argv=None):
    arg_parser = parser()
    args = arg_parser.parse_args(argv)
    sources = {
        name: getattr(args, name)
        for name in ("training", "rates", "initial", "holdout")
    }
    if args.synthetic:
        if any(sources.values()):
            arg_parser.error("--synthetic cannot be combined with input paths")
        if args.boundary_year != 2014:
            arg_parser.error(
                "the supplied synthetic fixture has boundary year 2014"
            )
        sources = write_synthetic_inputs(args.output_dir / "inputs")
    elif not all(sources.values()):
        arg_parser.error("supply all four input paths or --synthetic")
    try:
        run = run_mortality_graph(
            **sources,
            output_dir=args.output_dir,
            boundary_year=args.boundary_year,
            external_vintage_year=args.external_vintage_year,
            experiment_id=args.experiment_id,
            replicate=args.replicate,
            base_seed=args.base_seed,
        )
    except (ImportError, ValueError) as error:
        arg_parser.exit(2, f"{error}\n")
    print(
        f"{args.output_dir / 'report.json'}: engineering={run.report['engineering_verdict']}, fixture={run.report['fixture_verdict']}"
    )
    return (
        0
        if run.report["engineering_verdict"]
        == run.report["fixture_verdict"]
        == "pass"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
