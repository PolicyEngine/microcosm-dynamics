"""Record certified wheel identities in an already installed SSI interpreter.

Run this script with the isolated interpreter, not the project's Python.
It reads distribution metadata only and never imports policyengine_us.
PyPI wheel digests identify artifacts; installed RECORD digests bind files.
Updating the committed pin is a new reviewed certification step.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    args = parser.parse_args()
    versions = {
        name: metadata.version(name)
        for name in ("policyengine", "policyengine-us", "policyengine-core")
    }
    args.captures.mkdir(parents=True, exist_ok=True)
    wheels = {}
    captures = []
    for name, version in versions.items():
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urlopen(url) as response:
            content = response.read()
        retrieved = datetime.now(timezone.utc).isoformat()
        target = args.captures / f"{name}-{version}.json"
        target.write_bytes(content)
        captures.append(
            {
                "path": target.name,
                "url": url,
                "retrieved_utc": retrieved,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
        release = json.loads(content)
        candidates = [
            item
            for item in release["urls"]
            if item["filename"].endswith(".whl")
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"Expected one platform-independent wheel for {name}"
            )
        wheel = candidates[0]
        wheels[name] = {
            "version": version,
            "filename": wheel["filename"],
            "sha256": wheel["digests"]["sha256"],
            "size_bytes": wheel["size"],
            "url": wheel["url"],
            "uploaded_utc": wheel["upload_time_iso_8601"],
        }
    latest_url = "https://pypi.org/pypi/policyengine/json"
    with urlopen(latest_url) as response:
        content = response.read()
    (args.captures / "policyengine-latest.json").write_bytes(content)
    captures.append(
        {
            "path": "policyengine-latest.json",
            "url": latest_url,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    )
    latest = json.loads(content)["info"]["version"]
    if latest != versions["policyengine"]:
        raise ValueError(f"Installed interface is not latest: {latest}")
    pin = {
        "schema_version": 1,
        "versions": versions,
        "wheels": wheels,
        "record_sha256": {
            name: hashlib.sha256(
                metadata.distribution(name).read_text("RECORD").encode()
            ).hexdigest()
            for name in versions
        },
        "installed_distributions": dict(
            sorted(
                (dist.metadata["Name"], dist.version)
                for dist in metadata.distributions()
            )
        ),
        "latest_checked_utc": datetime.now(timezone.utc).isoformat(),
        "certification": "policyengine[us]==" + versions["policyengine"],
    }
    args.output.write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n")
    (args.captures / "capture_manifest.json").write_text(
        json.dumps(captures, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
