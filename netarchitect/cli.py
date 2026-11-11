"""
cli.py — Command-line interface for NetArchitect.

Usage examples:
  python -m netarchitect --preset campus
  python -m netarchitect --preset metro --export exports/
  python -m netarchitect --custom my_params.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from netarchitect.media import select_media
from netarchitect.routing import select_routing
from netarchitect.vlsm import allocate
from netarchitect.configgen import generate_configs
from netarchitect.explain import ArchitecturalLog
from netarchitect.validator import validate_custom_input


# ── Preset loader ──────────────────────────────────────────────────────────────

def _load_preset(name: str) -> dict:
    """Load a preset JSON from the presets/ directory."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "presets", f"{name}.json")
    if not os.path.exists(path):
        sys.exit(f"ERROR: Preset file not found: {path}")
    with open(path) as f:
        return json.load(f)


# ── Core pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(params: dict, export_dir: str | None = None) -> None:
    """Execute the full NetArchitect pipeline for *params*."""
    preset_name = params.get("preset", "custom")
    log = ArchitecturalLog()

    print(f"\n{'='*64}")
    print(f"  NetArchitect — {params.get('description', preset_name)}")
    print(f"{'='*64}\n")

    # ── 1. Media selection ─────────────────────────────────────────────────────
    print("── Physical Media Selection ──────────────────────────────────")
    for link in params.get("links", []):
        decision = select_media(link["distance_m"])
        log.add(f"Media: {link['name']}", decision)
        print(f"  {link['name']}")
        print(f"    Choice      : {decision.choice}")
        print(f"    Justification: {decision.justification[:100]}...")
        print()

    # ── 2. VLSM allocation ─────────────────────────────────────────────────────
    print("── VLSM Subnet Allocation ────────────────────────────────────")
    subnets_input = params.get("subnets", [])
    root_prefix   = params.get("root_prefix", "10.0.0.0/16")
    result = allocate(root_prefix, subnets_input)
    for s in result.subnets:
        print(f"  {s.name:20s}  {s.network}/{s.prefix}  mask {s.mask}  "
              f"usable {s.usable_hosts:>6}  util {s.utilization_pct:.1f}%")
    print(f"\n  Overall utilisation: {result.overall_utilization:.2f}%\n")

    # ── 3. Routing selection ───────────────────────────────────────────────────
    print("── Routing Protocol Selection ────────────────────────────────")
    routing = select_routing(
        num_subnets=len(result.subnets),
        num_as=params.get("num_as", 1),
        has_cloud=params.get("has_cloud", False),
        links=params.get("links", []),
    )
    log.add("Routing Protocol", routing)
    print(f"  Choice: {routing.choice}")
    print(f"  Reason: {routing.justification[:120]}...\n")

    # ── 4. Config generation ───────────────────────────────────────────────────
    print("── Device Configuration Generation ──────────────────────────")
    configs = generate_configs(preset_name, params)
    for device in configs:
        print(f"  Generated config for: {device}")
    print()

    # ── 5. Export ──────────────────────────────────────────────────────────────
    if export_dir:
        os.makedirs(export_dir, exist_ok=True)
        for device, cfg in configs.items():
            fname = os.path.join(export_dir, f"{device}.txt")
            with open(fname, "w") as f:
                f.write(cfg)
            print(f"  Exported: {fname}")

        rationale_path = os.path.join(export_dir, "rationale.md")
        with open(rationale_path, "w") as f:
            f.write(log.render_markdown())
        print(f"  Exported: {rationale_path}")
        print()

    print("── Architectural Rationale ───────────────────────────────────")
    print(log.render_text())


# ── Argument parser ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netarchitect",
        description="NetArchitect: Network Recommendation & Configuration Engine",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--preset",
        choices=["campus", "metro", "wan"],
        help="Use a built-in preset (campus | metro | wan)",
    )
    group.add_argument(
        "--custom",
        metavar="JSON_FILE",
        help="Path to a custom parameters JSON file",
    )
    parser.add_argument(
        "--export",
        metavar="DIR",
        default=None,
        help="Export device configs and rationale.md into DIR",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.preset:
        params = _load_preset(args.preset)
    else:
        with open(args.custom) as f:
            raw = json.load(f)
        params = validate_custom_input(raw)

    run_pipeline(params, export_dir=args.export)


if __name__ == "__main__":
    main()
