#!/usr/bin/env python3
"""Validate and persist a Claude project handoff for Hermes analysis."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path("/opt/data/inbox/claude-project-handoffs")
SUBSCRIPTIONS_PATH = Path("/opt/data/webhook_subscriptions.json")
ROUTE_NAME = "claude-project-handoff"
ALLOWED_PROJECTS = {"cabe", "vimeo-library"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,63}$")
MAX_REPORT_CHARS = 450_000


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def atomic_write(path: Path, content: str) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, path)


def consume_subscription() -> None:
    """Remove the dedicated route after one valid handoff."""
    if not SUBSCRIPTIONS_PATH.is_file():
        return
    data = json.loads(SUBSCRIPTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or ROUTE_NAME not in data:
        return
    del data[ROUTE_NAME]
    atomic_write(
        SUBSCRIPTIONS_PATH,
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    )
    SUBSCRIPTIONS_PATH.chmod(0o600)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        fail(f"invalid JSON: {exc}")

    if not isinstance(payload, dict):
        fail("payload must be a JSON object")
    if payload.get("schema_version") != 1:
        fail("schema_version must be 1")
    if payload.get("event_type") != "project_handoff":
        fail("event_type must be project_handoff")

    handoff_id = payload.get("handoff_id")
    if not isinstance(handoff_id, str) or not ID_RE.fullmatch(handoff_id):
        fail("handoff_id must be 8-64 safe characters")

    reports = payload.get("reports")
    if not isinstance(reports, list) or not 1 <= len(reports) <= 2:
        fail("reports must contain one or two entries")

    normalized: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for report in reports:
        if not isinstance(report, dict):
            fail("each report must be an object")
        slug = report.get("project_slug")
        title = report.get("title")
        markdown = report.get("report_markdown")
        if slug not in ALLOWED_PROJECTS or slug in seen:
            fail("project_slug must be unique and allowed")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            fail("title must contain 1-200 characters")
        if not isinstance(markdown, str) or not markdown.strip():
            fail("report_markdown must be non-empty")
        if len(markdown) > MAX_REPORT_CHARS:
            fail("individual report is too large")
        seen.add(slug)
        encoded = markdown.encode("utf-8")
        normalized.append(
            {
                "project_slug": slug,
                "title": title.strip(),
                "report_markdown": markdown,
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "bytes": len(encoded),
            }
        )

    if payload.get("validation_only") is True:
        print(json.dumps({"validated": True, "projects": sorted(seen)}))
        return

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    destination = BASE_DIR / handoff_id
    if destination.exists():
        manifest_path = destination / "manifest.json"
        if not manifest_path.is_file():
            fail("handoff_id already exists without a valid manifest")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {entry["project_slug"]: entry["sha256"] for entry in normalized}
        actual = {entry["project_slug"]: entry["sha256"] for entry in existing.get("reports", [])}
        if expected != actual:
            fail("handoff_id already exists with different content")
        consume_subscription()
        output = {
            "event_type": "project_handoff",
            "handoff_id": handoff_id,
            "manifest_path": str(manifest_path),
            "report_paths": [entry["path"] for entry in existing["reports"]],
            "received_projects": sorted(actual),
            "duplicate_payload": True,
        }
        print(json.dumps(output, ensure_ascii=False))
        return

    destination.mkdir(mode=0o700)
    manifest_reports: list[dict[str, str | int]] = []
    for report in normalized:
        report_path = destination / f"{report['project_slug']}.md"
        atomic_write(report_path, str(report["report_markdown"]))
        report_path.chmod(0o600)
        manifest_reports.append(
            {
                "project_slug": report["project_slug"],
                "title": report["title"],
                "path": str(report_path),
                "sha256": report["sha256"],
                "bytes": report["bytes"],
            }
        )

    manifest = {
        "schema_version": 1,
        "handoff_id": handoff_id,
        "sender": str(payload.get("sender", "claude"))[:100],
        "created_at": str(payload.get("created_at", ""))[:100],
        "received_at": datetime.now(timezone.utc).isoformat(),
        "reports": manifest_reports,
    }
    manifest_path = destination / "manifest.json"
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    manifest_path.chmod(0o600)
    consume_subscription()

    output = {
        "event_type": "project_handoff",
        "handoff_id": handoff_id,
        "manifest_path": str(manifest_path),
        "report_paths": [entry["path"] for entry in manifest_reports],
        "received_projects": sorted(seen),
        "duplicate_payload": False,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
