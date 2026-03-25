#!/usr/bin/env python3
"""GPU inventory helper for parameter-golf.

Source of truth:
- If /root/auto-research/auto_research.db exists, use it as the primary inventory.
- Otherwise fall back to the local infra/gpu_creds.sh registry.

This keeps parameter-golf autonomous while still allowing it to mirror the
platform DB when auto-research is available.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CREDS = REPO_ROOT / "infra" / "gpu_creds.sh"
DEFAULT_AUTO_DB = Path(os.environ.get("AUTO_RESEARCH_DB", "/root/auto-research/auto_research.db"))

ASSIGN_RE = re.compile(r"^([A-Z0-9_]+)=(.*)$")
GPU_RE = re.compile(r"^GPU_([A-Z0-9_]+)_(PORT|PASS|RATE|TYPE|USER|REPO_PATH)$")


@dataclass
class GPUEntry:
    name: str
    host: str | None = None
    port: int | None = None
    user: str = "root"
    password: str | None = None
    repo_path: str = "/root/parameter-golf"
    status: str | None = None
    gpu_type: str | None = None
    hourly_rate: float | None = None
    is_active: bool | None = None

    def to_list_row(self) -> str:
        password = self.password or ""
        return f"{self.name} {self.port or 22} {password}"

    def rate_value(self) -> str:
        return "" if self.hourly_rate is None else f"{self.hourly_rate:g}"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        try:
            return ast.literal_eval(value)
        except Exception:
            return value[1:-1]
    return value


def _read_local_inventory() -> dict[str, GPUEntry]:
    if not LOCAL_CREDS.exists():
        return {}

    host = None
    bucket: dict[str, dict[str, str]] = {}

    for raw_line in LOCAL_CREDS.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = ASSIGN_RE.match(line)
        if not match:
            continue

        key, raw_value = match.groups()
        value = _unquote(raw_value)

        if key == "HOST":
            host = value
            continue

        gpu_match = GPU_RE.match(key)
        if not gpu_match:
            continue

        name, field = gpu_match.groups()
        bucket.setdefault(name, {})[field] = value

    entries: dict[str, GPUEntry] = {}
    for name, fields in bucket.items():
        port_raw = fields.get("PORT")
        password = fields.get("PASS")
        if not port_raw or not password:
            continue

        entry = GPUEntry(
            name=name,
            host=host,
            port=int(port_raw),
            user=fields.get("USER", "root"),
            password=password,
            repo_path=fields.get("REPO_PATH", "/root/parameter-golf"),
            gpu_type=fields.get("TYPE"),
            hourly_rate=_parse_float(fields.get("RATE")),
            is_active=True,
        )
        entries[name] = entry

    return entries


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _read_auto_inventory(db_path: Path) -> dict[str, GPUEntry]:
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        columns = _table_columns(conn, "gpus")
        if not columns:
            return {}

        wanted = [
            "name",
            "host",
            "port",
            "user",
            "password",
            "repo_path",
            "status",
            "gpu_type",
            "hourly_rate",
            "is_active",
        ]
        selected = [col for col in wanted if col in columns]
        if not selected:
            return {}

        query = f"SELECT {', '.join(selected)} FROM gpus"
        result: dict[str, GPUEntry] = {}
        for row in conn.execute(query):
            row_map = dict(row)
            name = row_map.get("name")
            if not name:
                continue

            is_active = row_map.get("is_active")
            status = row_map.get("status")
            if is_active in {0, "0", False} or status in {"removed", "deleted", "inactive"}:
                continue

            entry = GPUEntry(
                name=name,
                host=row_map.get("host"),
                port=_parse_int(row_map.get("port")),
                user=row_map.get("user") or "root",
                password=row_map.get("password"),
                repo_path=row_map.get("repo_path") or "/root/parameter-golf",
                status=status,
                gpu_type=row_map.get("gpu_type"),
                hourly_rate=_parse_float(str(row_map.get("hourly_rate")) if row_map.get("hourly_rate") is not None else None),
                is_active=True if is_active is None else bool(is_active),
            )
            result[name] = entry
        return result
    finally:
        conn.close()


def _parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def merged_inventory() -> dict[str, GPUEntry]:
    local = _read_local_inventory()
    auto = _read_auto_inventory(DEFAULT_AUTO_DB)

    merged = dict(local)
    merged.update(auto)
    return dict(sorted(merged.items(), key=lambda item: item[0].lower()))


def _rewrite_local_creds(entry: GPUEntry) -> None:
    lines: list[str] = []
    if LOCAL_CREDS.exists():
        lines = LOCAL_CREDS.read_text().splitlines()

    prefix = f"GPU_{entry.name}_"
    kept: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith(prefix):
            continue
        kept.append(raw)

    if not kept or kept[-1].strip():
        kept.append("")

    kept.append(f"# {entry.name} (managed by infra/gpu_inventory.py)")
    kept.append(f"GPU_{entry.name}_PORT={entry.port or 22}")
    kept.append(f'GPU_{entry.name}_PASS="{entry.password or ""}"')
    if entry.hourly_rate is not None:
        kept.append(f"GPU_{entry.name}_RATE={entry.hourly_rate:g}")
    if entry.gpu_type:
        kept.append(f'GPU_{entry.name}_TYPE="{entry.gpu_type}"')
    if entry.user and entry.user != "root":
        kept.append(f'GPU_{entry.name}_USER="{entry.user}"')
    if entry.repo_path and entry.repo_path != "/root/parameter-golf":
        kept.append(f'GPU_{entry.name}_REPO_PATH="{entry.repo_path}"')

    LOCAL_CREDS.write_text("\n".join(kept).rstrip() + "\n")


def _upsert_auto_db(entry: GPUEntry, db_path: Path) -> None:
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    try:
        columns = _table_columns(conn, "gpus")
        if not columns:
            return

        values: dict[str, Any] = {
            "name": entry.name,
            "host": entry.host,
            "port": entry.port,
            "user": entry.user,
            "password": entry.password,
            "repo_path": entry.repo_path,
            "status": entry.status or "unknown",
            "gpu_type": entry.gpu_type,
            "hourly_rate": entry.hourly_rate,
            "is_active": 1 if entry.is_active is not False else 0,
        }
        values = {k: v for k, v in values.items() if k in columns and v is not None}
        if "name" not in values:
            raise ValueError("GPU name is required")

        cols = list(values.keys())
        placeholders = ", ".join(f":{c}" for c in cols)
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "name")
        sql = f"""
            INSERT INTO gpus ({', '.join(cols)})
            VALUES ({placeholders})
            ON CONFLICT(name) DO UPDATE SET {updates}
        """
        conn.execute(sql, values)
        conn.commit()
    finally:
        conn.close()


def cmd_list(_: argparse.Namespace) -> int:
    for entry in merged_inventory().values():
        print(entry.to_list_row())
    return 0


def cmd_rates(_: argparse.Namespace) -> int:
    for entry in merged_inventory().values():
        rate = entry.rate_value()
        if rate:
            print(f"{entry.name} {rate}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    entry = merged_inventory().get(args.name)
    if not entry:
        return 1
    value = getattr(entry, args.field)
    if value is None:
        return 1
    print(value)
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    entry = GPUEntry(
        name=args.name,
        host=args.host or read_default_host(),
        port=args.port,
        user=args.user,
        password=args.password,
        repo_path=args.repo_path,
        gpu_type=args.gpu_type or None,
        hourly_rate=args.rate,
        status=args.status,
        is_active=True,
    )
    _rewrite_local_creds(entry)
    _upsert_auto_db(entry, DEFAULT_AUTO_DB)
    print(f"Registered {entry.name} locally" + (" and in auto-research" if DEFAULT_AUTO_DB.exists() else ""))
    return 0


def read_default_host() -> str | None:
    if not LOCAL_CREDS.exists():
        return None
    for raw_line in LOCAL_CREDS.read_text().splitlines():
        line = raw_line.strip()
        match = ASSIGN_RE.match(line)
        if match and match.group(1) == "HOST":
            return _unquote(match.group(2))
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPU inventory helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Emit merged GPU inventory as: name port password").set_defaults(func=cmd_list)
    sub.add_parser("rates", help="Emit merged GPU rates as: name rate").set_defaults(func=cmd_rates)

    get = sub.add_parser("get", help="Get a single field from the merged inventory")
    get.add_argument("name")
    get.add_argument("field", choices=["host", "port", "user", "password", "repo_path", "status", "gpu_type", "hourly_rate", "is_active"])
    get.set_defaults(func=cmd_get)

    reg = sub.add_parser("register", help="Register a GPU locally and sync it to auto-research if present")
    reg.add_argument("name")
    reg.add_argument("port", type=int)
    reg.add_argument("password")
    reg.add_argument("--host", default=None)
    reg.add_argument("--user", default="root")
    reg.add_argument("--repo-path", default="/root/parameter-golf")
    reg.add_argument("--rate", type=float, default=None)
    reg.add_argument("--gpu-type", default=None)
    reg.add_argument("--status", default="unknown")
    reg.set_defaults(func=cmd_register)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
