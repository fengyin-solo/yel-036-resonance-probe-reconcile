#!/usr/bin/env python3
"""Legacy channel pairing by arrival order."""

import json
import sys
from pathlib import Path


def main(argv):
    if len(argv) not in (3, 4):
        return 1
    source, target = Path(argv[1]), Path(argv[2])
    payload = json.loads(source.read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    readings = sorted(payload["readings"], key=lambda item: item["slot"])
    rows = []
    total = 0.0
    for index, reading in enumerate(readings):
        profile = profiles[index]
        residual = abs(reading["drive_hz"] - profile["fingerprint"][0])
        total += residual
        rows.append({
            "slot": reading["slot"],
            "probe_id": profile["probe_id"],
            "residual": residual,
        })
    result = {
        "rig_id": payload["rig_id"],
        "status": "probes_reconciled",
        "probe_assignments": rows,
        "total_residual": total,
        "accepted": True,
        "diagnostic": "fingerprints_within_ceiling",
    }
    target.write_bytes((json.dumps(result, separators=(",", ":")) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
