# NetArchitect: Recommendation & Config Engine

A Python tool that automatically selects physical media, allocates subnets via VLSM, picks routing protocols, and generates device configurations for campus, metro, and WAN network topologies.

## Features

| Module | Capability |
|--------|-----------|
| `media.py` | Physical media selection (Cat6a/OM4/OS2 SMF) with optical power budget |
| `vlsm.py` | VLSM subnet allocator using pure bitwise integer math (no `ipaddress` module) |
| `routing.py` | Routing protocol selection (OSPF / Multi-area OSPF + eBGP) with RFC citations |
| `configgen.py` | IOS-style device config generation (never uses `allowed vlan all`) |
| `explain.py` | Architectural decision logger (text + Markdown output) |
| `validator.py` | Custom JSON input validation |
| `cli.py` | argparse CLI with `--preset` and `--custom` modes |

## Quick Start

```bash
pip install -r requirements.txt

# Run a built-in preset
python -m netarchitect --preset campus
python -m netarchitect --preset metro
python -m netarchitect --preset wan

# Export device configs and rationale
python -m netarchitect --preset metro --export exports/

# Use custom parameters
python -m netarchitect --custom my_params.json
```

## Project Structure

```
miniproject-cn/
  presets/
    campus.json        3-building campus LAN
    metro.json         HQ + 2 remote sites MAN
    wan.json           4-city global WAN + cloud VPC
  netarchitect/
    __init__.py
    __main__.py        Entry point for python -m netarchitect
    errors.py          Custom exceptions
    validator.py       Input validation
    media.py           Physical media selection
    vlsm.py            VLSM allocator (pure bitwise math)
    routing.py         Routing protocol selection
    configgen.py       Device config generation
    explain.py         Architectural decision logger
    cli.py             CLI (argparse)
  tests/
    test_media.py
    test_vlsm.py
    test_routing.py
    test_configgen.py
  exports/             Output directory for generated configs
  README.md
  requirements.txt
  ai_audit_log.md
  bug_journal.md
```

## Media Selection Rules

| Distance | Medium | Transceiver | Standard |
|----------|--------|-------------|----------|
| ≤ 100 m | Cat6a UTP | 10GBASE-T | IEEE 802.3an |
| 101–400 m | OM4 MMF | 10GBASE-SR | IEEE 802.3ae |
| 401–10 000 m | OS2 SMF | 10GBASE-LR | IEEE 802.3ae |
| > 10 000 m | OS2 SMF | 10GBASE-ER | IEEE 802.3ae |

Optical power budget is computed for all SMF links and included in the justification.

## Running Tests

```bash
pytest tests/ -v
```

All 30 tests should pass.

## Custom Parameters Format

```json
{
  "preset": "custom",
  "description": "My network",
  "links": [
    {"name": "link-1", "distance_m": 150}
  ],
  "subnets": [
    {"name": "Users", "hosts": 200}
  ],
  "root_prefix": "192.168.0.0/22",
  "num_as": 1,
  "has_cloud": false
}
```
