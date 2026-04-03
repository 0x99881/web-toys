from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .constants import (
    INCOME_META_SHEET,
    INCOME_NAME_HEADER,
    NAME_HEADER,
    TOTAL_HEADER,
    WEAR_META_SHEET,
    WEAR_NAME_HEADER,
    WEAR_TOTAL_HEADER,
    WINDOW_SIZE,
)


class StoreWriteMixin:
    def _parse_decimal(self, value: str, field_name: str) -> Decimal:
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"{field_name}必须是数字。") from exc

    def _round_wear(self, value: Decimal | float | int) -> float:
        return round(float(value), 1)

    def _round_income(self, value: Decimal | float | int) -> float:
        return round(float(value), 1)

    # ????????????????????????
    def save_scores_and_wear(self, date_text: str, entries: list[dict[str, str]]) -> dict[str, Any]:
        workbook = self._open_workbook()
        self._ensure_score_sheet_structure(workbook)
        self._ensure_wear_sheet_structure(workbook)
        self._ensure_income_sheet_structure(workbook)
        score_sheet = self._score_sheet(workbook)
        wear_sheet = self._wear_sheet(workbook)
        income_sheet = self._income_sheet(workbook)

        total_col = self._find_column(score_sheet, TOTAL_HEADER)
        name_col = self._find_column(score_sheet, NAME_HEADER)
        if total_col is None or name_col is None:
            workbook.close()
            raise ValueError("积分表结构异常。")

        d_cols = self._d_columns(score_sheet)
        next_number = d_cols[-1][0] + 1 if d_cols else 1
        score_sheet.insert_cols(total_col, 1)
        target_col = total_col
        score_sheet.cell(1, target_col, f"D{next_number}")
        total_col += 1
        name_col = total_col + 1

        wear_total_col = self._find_column(wear_sheet, WEAR_TOTAL_HEADER)
        wear_name_col = self._find_column(wear_sheet, WEAR_NAME_HEADER)
        if wear_total_col is None or wear_name_col is None:
            workbook.close()
            raise ValueError("磨损表结构异常。")

        wear_cols = self._wear_columns(wear_sheet)
        next_wear_number = wear_cols[-1][0] + 1 if wear_cols else 1
        wear_sheet.insert_cols(wear_total_col, 1)
        wear_target_col = wear_total_col
        wear_sheet.cell(1, wear_target_col, date_text[5:].replace("-", ""))
        wear_total_col += 1
        wear_name_col = wear_total_col + 1

        income_name_col = self._find_column(income_sheet, INCOME_NAME_HEADER)
        if income_name_col is None:
            workbook.close()
            raise ValueError("收入表结构异常。")
        income_cols = self._income_columns(income_sheet)
        next_income_number = income_cols[-1][0] + 1 if income_cols else 1
        income_sheet.insert_cols(income_name_col, 1)
        income_target_col = income_name_col
        income_sheet.cell(1, income_target_col, date_text[5:].replace("-", ""))
        income_name_col += 1

        row_by_name = self._ensure_member_rows(
            score_sheet,
            name_col=name_col,
            total_col=total_col,
            value_columns=[col for _, col in self._d_columns(score_sheet)],
        )
        wear_row_by_name = self._ensure_member_rows(
            wear_sheet,
            name_col=wear_name_col,
            total_col=wear_total_col,
            value_columns=[col for _, col in self._wear_columns(wear_sheet)],
        )
        income_row_by_name = self._ensure_member_rows(
            income_sheet,
            name_col=income_name_col,
            total_col=None,
            value_columns=[col for _, col in self._income_columns(income_sheet)],
        )

        wear_rows_added = 0
        for entry in entries:
            name = entry["name"]
            score_text = entry.get("score", "").strip()
            before_text = entry.get("before_balance", "").strip()
            after_text = entry.get("after_balance", "").strip()
            manual_wear_text = entry.get("manual_wear", "").strip()
            income_text = entry.get("income", "").strip()

            score_value = int(score_text) if score_text else 0
            score_sheet.cell(row_by_name[name], target_col, score_value)
            wear_sheet.cell(wear_row_by_name[name], wear_target_col, 0)
            income_value = self._round_income(self._parse_decimal(income_text, f"{name} 的收入") if income_text else 0)
            income_sheet.cell(income_row_by_name[name], income_target_col, income_value)

            has_balance_input = bool(before_text or after_text)
            has_manual_input = bool(manual_wear_text)
            has_any_wear_input = has_balance_input or has_manual_input

            if not has_any_wear_input:
                continue

            if has_manual_input:
                wear_value = self._parse_decimal(manual_wear_text, f"{name} 的手动磨损")
                before_value = self._parse_decimal(before_text, f"{name} 的交易前余额") if before_text else None
                after_value = self._parse_decimal(after_text, f"{name} 的交易后余额") if after_text else None
            else:
                if not before_text or not after_text:
                    workbook.close()
                    raise ValueError(f"{name} 的交易前余额和交易后余额要么都填，要么都不填。")
                before_value = self._parse_decimal(before_text, f"{name} 的交易前余额")
                after_value = self._parse_decimal(after_text, f"{name} 的交易后余额")
                wear_value = before_value - after_value

            wear_sheet.cell(wear_row_by_name[name], wear_target_col, self._round_wear(wear_value))
            wear_rows_added += 1

        recent_numbers = [number for number, _ in self._d_columns(score_sheet)][-WINDOW_SIZE:]
        self._recalculate_totals(score_sheet, total_col)
        self._sort_named_rows(score_sheet, total_col, name_col)
        self._format_score_sheet(score_sheet, recent_numbers, total_col)
        self._recalculate_wear_totals(wear_sheet, wear_total_col)
        self._sort_named_rows(wear_sheet, wear_total_col, wear_name_col)
        self._sort_rows_by_name(income_sheet, income_name_col)
        self._append_meta(workbook, date_text, f"D{next_number}")
        self._append_wear_meta(workbook, date_text, str(next_wear_number))
        self._append_income_meta(workbook, date_text, str(next_income_number))
        self._save_workbook(workbook)
        workbook.close()
        return {
            "target_column": f"D{next_number}",
            "wear_column": date_text[5:].replace("-", ""),
            "wear_rows_added": wear_rows_added,
            "window_size": min(WINDOW_SIZE, len(recent_numbers)),
        }

