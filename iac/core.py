from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


class IntegrityError(RuntimeError):
    """Persisted continuity data failed integrity validation."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".iac-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical(value) + b"\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"Invalid or unreadable {path.name}: {exc}") from exc


def initialize(directory: str | Path) -> Path:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    manifests = {
        "identity.json": {
            "schema": 1,
            "core_name": "Independent AI Core",
            "core_version": "0.1.0",
            "identity_statement": "Portable system descriptor; not a claim of consciousness.",
            "invariants": [
                "Model and chat interface are replaceable execution components.",
                "Claims retain provenance and evidence status.",
                "No capability is claimed without implementation and tests."
            ]
        },
        "governance.json": {
            "schema": 1,
            "permissions": {
                "network": False,
                "external_actions": False,
                "self_modification": False,
                "write_scope": "this_store_only"
            },
            "note": "Declarative policy only; host runtime must enforce it."
        },
        "state.json": {
            "schema": 1, "status": "initialized", "active_task": None,
            "event_count": 0, "head_hash": GENESIS
        }
    }
    for name, value in manifests.items():
        path = root / name
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
        write_json(path, value)
    journal = root / "events.jsonl"
    if journal.exists():
        raise FileExistsError(f"Refusing to overwrite {journal}")
    atomic_write(journal, b"")
    return root


def verify_events(root: str | Path) -> tuple[int, str]:
    journal = Path(root) / "events.jsonl"
    try:
        raw = journal.read_bytes()
    except OSError as exc:
        raise IntegrityError(f"Missing event journal: {exc}") from exc
    if raw and not raw.endswith(b"\n"):
        raise IntegrityError("Journal ends with an incomplete record")
    previous, expected_seq = GENESIS, 1
    for line_number, line in enumerate(raw.splitlines(), start=1):
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError(f"Malformed event at line {line_number}") from exc
        if not isinstance(event, dict) or "hash" not in event:
            raise IntegrityError(f"Invalid event shape at line {line_number}")
        body = {key: value for key, value in event.items() if key != "hash"}
        if body.get("seq") != expected_seq:
            raise IntegrityError(f"Sequence mismatch at line {line_number}")
        if body.get("prev_hash") != previous:
            raise IntegrityError(f"Chain-link mismatch at line {line_number}")
        actual_hash = digest(body)
        if event["hash"] != actual_hash:
            raise IntegrityError(f"Hash mismatch at line {line_number}")
        previous, expected_seq = actual_hash, expected_seq + 1
    return expected_seq - 1, previous


def verify_store(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    read_json(root / "identity.json")
    read_json(root / "governance.json")
    state = read_json(root / "state.json")
    event_count, head_hash = verify_events(root)
    if state.get("event_count") != event_count or state.get("head_hash") != head_hash:
        raise IntegrityError("State checkpoint does not match verified event journal")
    return {"valid": True, "events": event_count, "head_hash": head_hash}


def append_event(root: str | Path, event_type: str,
                 payload: dict[str, Any]) -> dict[str, Any]:
    root = Path(root)
    if not event_type or not isinstance(payload, dict):
        raise ValueError("event_type must be non-empty and payload must be an object")
    event_count, previous_hash = verify_events(root)
    body = {
        "seq": event_count + 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "payload": payload,
        "prev_hash": previous_hash
    }
    event = dict(body, hash=digest(body))
    # v0.1 is single-writer: concurrent appenders must be serialized externally.
    with (root / "events.jsonl").open("ab") as stream:
        stream.write(canonical(event) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    state = read_json(root / "state.json")
    state["event_count"] = event_count + 1
    state["head_hash"] = event["hash"]
    state["status"] = "active"
    write_json(root / "state.json", state)
    return event


def export_verified(source: str | Path, destination: str | Path) -> dict[str, Any]:
    source, destination = Path(source), Path(destination)
    before = verify_store(source)
    destination.mkdir(parents=True, exist_ok=False)
    for name in ("identity.json", "governance.json", "state.json", "events.jsonl"):
        atomic_write(destination / name, (source / name).read_bytes())
    after = verify_store(destination)
    if before != after:
        raise IntegrityError("Export verification mismatch")
    return after
