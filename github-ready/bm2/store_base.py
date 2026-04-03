from __future__ import annotations

import json
from datetime import datetime

from openpyxl import load_workbook
from pathlib import Path
from typing import Any

from .constants import (
    CONFIG_FILE,
    DATA_FILE_PATTERNS,
    DEFAULT_MEMBERS,
    DEFAULT_QUICK_SCORES,
    DISABLED,
    DISABLED_ALIASES,
    ENABLED,
    ENABLED_ALIASES,
)


class StoreBaseMixin:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.config_path = base_dir / "system_config.json"
        self._ensure_member_config()
        self.workbook_path = self._resolve_workbook_path()
        self._ensure_workbook()

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _normalize_status(self, raw: str) -> str:
        if raw in DISABLED_ALIASES:
            return DISABLED
        return ENABLED

    def _load_config(self) -> dict[str, Any]:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        return {}

    def _save_config(self, config: dict[str, Any]) -> None:
        self.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _default_members(self) -> list[dict[str, str]]:
        now_text = self._timestamp()
        return [
            {"name": name, "status": ENABLED, "note": "", "created_at": now_text, "disabled_at": ""}
            for name in DEFAULT_MEMBERS
        ]

    # ???????????????
    def _ensure_member_config(self) -> None:
        config = self._load_config()
        changed = False
        members = config.get("members")
        if not isinstance(members, list):
            config["members"] = self._default_members()
            changed = True
        else:
            known_names = {str(item.get("name", "")).strip() for item in members if isinstance(item, dict)}
            for name in DEFAULT_MEMBERS:
                if name not in known_names:
                    members.append(
                        {
                            "name": name,
                            "status": ENABLED,
                            "note": "",
                            "created_at": self._timestamp(),
                            "disabled_at": "",
                        }
                    )
                    changed = True
            config["members"] = members
        if "quick_scores" not in config:
            config["quick_scores"] = DEFAULT_QUICK_SCORES
            changed = True
        if changed:
            self._save_config(config)

    def get_members(self) -> list[dict[str, str]]:
        self._ensure_member_config()
        config = self._load_config()
        result = []
        for item in config.get("members", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            result.append(
                {
                    "name": name,
                    "status": self._normalize_status(str(item.get("status") or ENABLED)),
                    "note": str(item.get("note") or ""),
                    "created_at": str(item.get("created_at") or ""),
                    "disabled_at": str(item.get("disabled_at") or ""),
                }
            )
        result.sort(key=lambda item: item["name"])
        return result

    def get_member(self, name: str) -> dict[str, str] | None:
        for member in self.get_members():
            if member["name"] == name:
                return member
        return None

    def get_active_members(self) -> list[dict[str, str]]:
        return [item for item in self.get_members() if item["status"] == ENABLED]

    def add_member(self, name: str, note: str = "") -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("成员姓名不能为空。")
        members = self.get_members()
        if any(item["name"] == cleaned for item in members):
            raise ValueError("成员已存在。")
        config = self._load_config()
        config.setdefault("members", members)
        config["members"].append(
            {
                "name": cleaned,
                "status": ENABLED,
                "note": note.strip(),
                "created_at": self._timestamp(),
                "disabled_at": "",
            }
        )
        self._save_config(config)
        workbook = self._open_workbook()
        self._ensure_score_sheet_structure(workbook)
        self._ensure_wear_sheet_structure(workbook)
        self._ensure_income_sheet_structure(workbook)
        self._save_workbook(workbook)
        workbook.close()

    def update_member(self, name: str, note: str, status: str | None = None) -> None:
        config = self._load_config()
        members = config.get("members", [])
        found = False
        for item in members:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).strip() != name:
                continue
            found = True
            item["note"] = note.strip()
            if status in {ENABLED, DISABLED}:
                previous = self._normalize_status(str(item.get("status") or ENABLED))
                item["status"] = status
                if status == DISABLED and previous != DISABLED:
                    item["disabled_at"] = self._timestamp()
                if status == ENABLED:
                    item["disabled_at"] = ""
            break
        if not found:
            raise ValueError("成员不存在。")
        config["members"] = members
        self._save_config(config)

    def get_quick_scores(self) -> list[int]:
        config = self._load_config()
        return [int(value) for value in config.get("quick_scores", DEFAULT_QUICK_SCORES)]

    def _resolve_workbook_path(self) -> Path:
        config = self._load_config()
        configured = config.get("excel_filename")
        if configured:
            candidate = self.base_dir / configured
            if candidate.exists():
                return candidate
        existing: list[Path] = []
        for pattern in DATA_FILE_PATTERNS:
            existing.extend(self.base_dir.glob(pattern))
        existing = sorted(set(existing))
        target = existing[0] if existing else self.base_dir / f"BM2记录_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        config["excel_filename"] = target.name
        self._save_config(config)
        return target

    def _open_workbook(self):
        return load_workbook(self.workbook_path)

    def _save_workbook(self, workbook) -> None:
        try:
            workbook.save(self.workbook_path)
        except PermissionError as exc:
            raise ValueError(f"Excel 文件正在被占用，请先关闭 {self.workbook_path.name} 后再重试。") from exc

