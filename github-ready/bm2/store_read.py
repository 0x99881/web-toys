from __future__ import annotations

import calendar
from datetime import datetime
from typing import Any

from .constants import (
    INCOME_META_SHEET,
    INCOME_NAME_HEADER,
    NAME_HEADER,
    TOTAL_HEADER,
    WEAR_META_SHEET,
    WEAR_NAME_HEADER,
    WINDOW_SIZE,
)


class StoreReadMixin:
    def get_score_rankings(self, limit: int = 999) -> list[dict[str, int | str]]:
        workbook = self._open_workbook()
        self._ensure_score_sheet_structure(workbook)
        sheet = self._score_sheet(workbook)
        total_col = self._find_column(sheet, TOTAL_HEADER)
        name_col = self._find_column(sheet, NAME_HEADER)
        rows = []
        if total_col and name_col:
            for row in range(2, sheet.max_row + 1):
                name = sheet.cell(row, name_col).value
                total = sheet.cell(row, total_col).value
                if name:
                    rows.append({"name": str(name), "total": int(total or 0)})
        workbook.close()
        rows.sort(key=lambda item: (-int(item["total"]), str(item["name"])))
        return rows[:limit]

    def get_score_summary(self) -> dict[str, Any]:
        workbook = self._open_workbook()
        self._ensure_score_sheet_structure(workbook)
        sheet = self._score_sheet(workbook)
        d_cols = self._d_columns(sheet)
        workbook.close()
        return {
            "latest_column": f"D{d_cols[-1][0]}" if d_cols else "-",
            "window_size": min(WINDOW_SIZE, len(d_cols)),
            "rankings": self.get_score_rankings(limit=999),
        }

    def _get_member_value_records(
        self,
        *,
        name: str,
        year_hint: int | None,
        sheet_getter,
        ensure_structure,
        meta_sheet_name: str,
        name_header: str,
        columns_getter,
        value_key: str,
        value_formatter,
    ) -> list[dict[str, Any]]:
        workbook = self._open_workbook()
        ensure_structure(workbook)
        sheet = sheet_getter(workbook)
        date_by_number = self._meta_to_date_map(workbook, meta_sheet_name)
        name_col = self._find_column(sheet, name_header)
        rows = []
        if year_hint is None:
            year_hint = datetime.now().year
        if name_col is not None:
            target_row = None
            for row in range(2, sheet.max_row + 1):
                if str(sheet.cell(row, name_col).value or "") == name:
                    target_row = row
                    break
            if target_row is not None:
                for number, col in columns_getter(sheet):
                    raw_date = date_by_number.get(number, str(sheet.cell(1, col).value))
                    rows.append(
                        {
                            "date": self._normalize_wear_date_text(raw_date, year_hint),
                            value_key: value_formatter(sheet.cell(target_row, col).value or 0),
                        }
                    )
        workbook.close()
        rows.sort(key=lambda item: item["date"])
        return rows

    def get_member_wear_records(self, name: str, year_hint: int | None = None) -> list[dict[str, Any]]:
        return self._get_member_value_records(
            name=name,
            year_hint=year_hint,
            sheet_getter=self._wear_sheet,
            ensure_structure=self._ensure_wear_sheet_structure,
            meta_sheet_name=WEAR_META_SHEET,
            name_header=WEAR_NAME_HEADER,
            columns_getter=self._wear_columns,
            value_key="wear",
            value_formatter=self._round_wear,
        )

    def get_member_income_records(self, name: str, year_hint: int | None = None) -> list[dict[str, Any]]:
        return self._get_member_value_records(
            name=name,
            year_hint=year_hint,
            sheet_getter=self._income_sheet,
            ensure_structure=self._ensure_income_sheet_structure,
            meta_sheet_name=INCOME_META_SHEET,
            name_header=INCOME_NAME_HEADER,
            columns_getter=self._income_columns,
            value_key="income",
            value_formatter=self._round_income,
        )

    def get_wear_sheet_view(self) -> dict[str, Any]:
        workbook = self._open_workbook()
        self._ensure_wear_sheet_structure(workbook)
        sheet = self._wear_sheet(workbook)
        headers = [sheet.cell(1, col).value for col in range(1, sheet.max_column + 1)]
        rows = []
        name_col = self._find_column(sheet, WEAR_NAME_HEADER)
        for row in range(2, sheet.max_row + 1):
            values = [sheet.cell(row, col).value for col in range(1, sheet.max_column + 1)]
            if name_col is not None and not values[name_col - 1]:
                continue
            rows.append(values)
        workbook.close()
        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(headers),
        }

    def get_member_calendar(self, name: str, year: int, month: int) -> dict[str, Any]:
        wear_records = self.get_member_wear_records(name, year_hint=year)
        income_records = self.get_member_income_records(name, year_hint=year)
        merged_map: dict[str, dict[str, Any]] = {}

        for item in wear_records:
            merged_map.setdefault(item["date"], {"date": item["date"], "wear": 0.0, "income": 0.0, "note": ""})
            merged_map[item["date"]]["wear"] = item["wear"]
        for item in income_records:
            merged_map.setdefault(item["date"], {"date": item["date"], "wear": 0.0, "income": 0.0, "note": ""})
            merged_map[item["date"]]["income"] = item["income"]

        records = sorted(merged_map.values(), key=lambda item: item["date"])
        month_prefix = f"{year:04d}-{month:02d}-"
        month_records = [item for item in records if item["date"].startswith(month_prefix)]
        record_map = {item["date"]: item for item in month_records}
        max_abs_wear = max((abs(float(item["wear"])) for item in month_records), default=0.0)

        cal = calendar.Calendar(firstweekday=0)
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            cells = []
            for day in week:
                date_text = day.strftime("%Y-%m-%d")
                record = record_map.get(date_text)
                wear = None if record is None else float(record["wear"])
                income = None if record is None else float(record["income"])
                intensity = 0.0 if record is None or max_abs_wear == 0 else abs(wear) / max_abs_wear
                cells.append(
                    {
                        "date": date_text,
                        "day": day.day,
                        "in_month": day.month == month,
                        "wear": wear,
                        "income": income,
                        "note": "" if record is None else str(record.get("note", "")),
                        "wear_account_count": 0 if wear in (None, 0.0) else 1,
                        "income_account_count": 0 if record is None else (1 if income not in (None, 0.0) else 0),
                        "avg_wear": wear,
                        "avg_income": income,
                        "breakdown": [],
                        "intensity": round(intensity, 3),
                    }
                )
            weeks.append(cells)

        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        return {
            "year": year,
            "month": month,
            "month_label": f"{year}?{month:02d}?",
            "weeks": weeks,
            "records": sorted(month_records, key=lambda item: item["date"], reverse=True),
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
        }

    def _get_all_members_calendar(self, year: int, month: int) -> dict[str, Any]:
        merged_map: dict[str, dict[str, Any]] = {}
        for member in self.get_members():
            member_name = member["name"]
            member_calendar = self.get_member_calendar(member_name, year, month)
            for item in member_calendar["records"]:
                merged_map.setdefault(
                    item["date"],
                    {
                        "date": item["date"],
                        "wear": 0.0,
                        "income": 0.0,
                        "note": "",
                        "wear_account_count": 0,
                        "income_account_count": 0,
                        "breakdown": [],
                    },
                )
                wear_value = float(item.get("wear", 0) or 0)
                income_value = float(item.get("income", 0) or 0)
                merged_map[item["date"]]["wear"] = self._round_wear(float(merged_map[item["date"]]["wear"]) + wear_value)
                merged_map[item["date"]]["income"] = self._round_income(float(merged_map[item["date"]]["income"]) + income_value)
                if wear_value != 0:
                    merged_map[item["date"]]["wear_account_count"] = int(merged_map[item["date"]]["wear_account_count"]) + 1
                if income_value != 0:
                    merged_map[item["date"]]["income_account_count"] = int(merged_map[item["date"]]["income_account_count"]) + 1
                if wear_value != 0 or income_value != 0:
                    merged_map[item["date"]]["breakdown"].append(
                        {
                            "name": member_name,
                            "wear": self._round_wear(wear_value),
                            "income": self._round_income(income_value),
                        }
                    )

        records = sorted(merged_map.values(), key=lambda item: item["date"])
        month_prefix = f"{year:04d}-{month:02d}-"
        month_records = [item for item in records if item["date"].startswith(month_prefix)]
        for item in month_records:
            wear_count = int(item.get("wear_account_count", 0) or 0)
            income_count = int(item.get("income_account_count", 0) or 0)
            item["avg_wear"] = self._round_wear(float(item["wear"]) / wear_count) if wear_count else 0.0
            item["avg_income"] = self._round_income(float(item["income"]) / income_count) if income_count else 0.0
            item["breakdown"].sort(key=lambda row: (-abs(float(row["wear"])), row["name"]))

        record_map = {item["date"]: item for item in month_records}
        max_abs_wear = max((abs(float(item["wear"])) for item in month_records), default=0.0)

        cal = calendar.Calendar(firstweekday=0)
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            cells = []
            for day in week:
                date_text = day.strftime("%Y-%m-%d")
                record = record_map.get(date_text)
                wear = None if record is None else float(record["wear"])
                income = None if record is None else float(record["income"])
                intensity = 0.0 if record is None or max_abs_wear == 0 else abs(wear) / max_abs_wear
                cells.append(
                    {
                        "date": date_text,
                        "day": day.day,
                        "in_month": day.month == month,
                        "wear": wear,
                        "income": income,
                        "avg_wear": None if record is None else float(record.get("avg_wear", 0)),
                        "avg_income": None if record is None else float(record.get("avg_income", 0)),
                        "wear_account_count": 0 if record is None else int(record.get("wear_account_count", 0) or 0),
                        "income_account_count": 0 if record is None else int(record.get("income_account_count", 0) or 0),
                        "breakdown": [] if record is None else record.get("breakdown", []),
                        "note": "??????" if record is not None else "",
                        "intensity": round(intensity, 3),
                    }
                )
            weeks.append(cells)

        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        return {
            "year": year,
            "month": month,
            "month_label": f"{year}?{month:02d}?",
            "weeks": weeks,
            "records": sorted(month_records, key=lambda item: item["date"], reverse=True),
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
        }

    # ?????????????????????
    def get_member_profit_calendar(self, name: str, year: int, month: int) -> dict[str, Any]:
        calendar_data = self._get_all_members_calendar(year, month) if name == "all" else self.get_member_calendar(name, year, month)
        month_records = calendar_data["records"]
        month_income = self._round_income(sum(float(item.get("income", 0) or 0) for item in month_records))
        month_wear = self._round_wear(sum(float(item.get("wear", 0) or 0) for item in month_records))
        active_member_count = len(self.get_active_members()) if name == "all" else len(month_records)
        total_income_account_count = active_member_count
        total_wear_account_count = active_member_count
        avg_income = self._round_income(month_income / total_income_account_count) if total_income_account_count else 0.0
        avg_wear = self._round_wear(month_wear / total_wear_account_count) if total_wear_account_count else 0.0
        today_text = datetime.now().strftime("%Y-%m-%d")
        return {
            **calendar_data,
            "month_income_total": month_income,
            "month_wear_total": month_wear,
            "month_avg_income": avg_income,
            "month_avg_wear": avg_wear,
            "month_income_account_count": total_income_account_count,
            "month_wear_account_count": total_wear_account_count,
            "today": today_text,
            "is_all_members": name == "all",
        }
