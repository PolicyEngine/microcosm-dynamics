"""Record every installed wheel, matching installed WHEEL tags to PyPI.

Run with the isolated SSI interpreter. Digests come from pinned PyPI release
metadata; this script does not download the wheel archives a second time.
The output includes a platform-specific, hash-locked reproduction file.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from packaging.utils import canonicalize_name, parse_wheel_filename


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    args = parser.parse_args()
    args.captures.mkdir(parents=True, exist_ok=True)
    distributions = list(metadata.distributions())

    def receipt(dist):
        name = canonicalize_name(dist.metadata["Name"])
        version = dist.version
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urlopen(url) as response:
            content = response.read()
        retrieved = datetime.now(timezone.utc).isoformat()
        path = f"{name}-{version}.json"
        (args.captures / path).write_bytes(content)
        tags = {
            line.removeprefix("Tag: ")
            for line in dist.read_text("WHEEL").splitlines()
            if line.startswith("Tag: ")
        }
        wheels = [
            item
            for item in json.loads(content)["urls"]
            if item["filename"].endswith(".whl")
            and {str(tag) for tag in parse_wheel_filename(item["filename"])[3]}
            == tags
        ]
        if len(wheels) != 1:
            raise ValueError(
                f"Cannot identify one installed wheel: {name}: {tags}"
            )
        wheel = wheels[0]
        return (
            name,
            {
                "version": version,
                "filename": wheel["filename"],
                "sha256": wheel["digests"]["sha256"],
                "url": wheel["url"],
                "size_bytes": wheel["size"],
                "installed_wheel_tags": sorted(tags),
            },
            {
                "path": path,
                "url": url,
                "retrieved_utc": retrieved,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            },
        )

    # Independent read-only metadata requests; no custom headers or retries.
    with ThreadPoolExecutor(max_workers=4) as executor:
        entries = list(executor.map(receipt, distributions))
    wheels = {name: wheel for name, wheel, _ in sorted(entries)}
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "digest_provenance": "PyPI release metadata matched to installed WHEEL tags",
                "wheels": wheels,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (args.captures / "capture_manifest.json").write_text(
        json.dumps(
            [capture for _, _, capture in sorted(entries)],
            indent=2,
        )
        + "\n"
    )
    args.requirements.write_text(
        "# Certified SSI0 environment: CPython 3.13, macOS arm64.\n"
        + "\n".join(
            f"{name}=={wheel['version']} --hash=sha256:{wheel['sha256']}"
            for name, wheel in wheels.items()
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
