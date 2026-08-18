#!/bin/bash
cd /Users/maxghenis/PolicyEngine/social-security-model-worktrees/ci-shard
uv venv --allow-existing >/dev/null 2>&1
uv pip install -e ".[dev]" pytest-split >/dev/null 2>&1
uv run --no-sync pytest -q --store-durations 2>&1 | tail -3 > .durations-run.log
echo $? >> .durations-run.log
