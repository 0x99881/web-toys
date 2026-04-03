from __future__ import annotations

from typing import Any

from .constants import (
    INCOME_NAME_HEADER,
    INCOME_SHEET,
    INCOME_SHEET_ALIASES,
    NAME_HEADER,
    SCORE_SHEET,
    SCORE_SHEET_ALIASES,
    TOTAL_HEADER,
    WEAR_NAME_HEADER,
    WEAR_SHEET,
    WEAR_SHEET_ALIASES,
)


class StoreSheetUtilsMixin:
    def _find_sheet_by_alias(self, workbook, aliases: list[str]):
        for name in aliases:
            if name in workbook.sheetnames:
                return workbook[name]
        return None

    def _ensure_named_sheet(self, workbook, primary_name: str, aliases: list[str], headers: list[str], hidden: bool = False):
        sheet = self._find_sheet_by_alias(workbook, aliases)
        changed = False
        if sheet is None:
            sheet = workbook.create_sheet(title=primary_name)
            sheet.append(headers)
            changed = True
        elif sheet.title != primary_name:
            sheet.title = primary_name
            changed = True

        current_headers = [sheet.cell(1, idx).value for idx in range(1, len(headers) + 1)]
        if current_headers != headers:
            if primary_name == WEAR_SHEET and sheet.max_row > 1:
                if LEGACY_WEAR_SHEET in workbook.sheetnames:
                    workbook.remove(workbook[LEGACY_WEAR_SHEET])
                sheet.title = LEGACY_WEAR_SHEET
                sheet = workbook.create_sheet(title=primary_name)
                sheet.append(headers)
            else:
                sheet.delete_rows(1, sheet.max_row)
                sheet.append(headers)
            changed = True

        if hidden and sheet.sheet_state != "hidden":
            sheet.sheet_state = "hidden"
            changed = True
        return sheet, changed

    def _wear_sheet(self, workbook):
        sheet = self._find_sheet_by_alias(workbook, WEAR_SHEET_ALIASES)
        if sheet is not None:
            if sheet.title != WEAR_SHEET:
                sheet.title = WEAR_SHEET
            return sheet
        return workbook.create_sheet(title=WEAR_SHEET)

    def _income_sheet(self, workbook):
        sheet = self._find_sheet_by_alias(workbook, INCOME_SHEET_ALIASES)
        if sheet is not None:
            if sheet.title != INCOME_SHEET:
                sheet.title = INCOME_SHEET
            return sheet
        return workbook.create_sheet(title=INCOME_SHEET)

    def _score_sheet(self, workbook):
        sheet = self._find_sheet_by_alias(workbook, SCORE_SHEET_ALIASES)
        if sheet is not None:
            if sheet.title != SCORE_SHEET:
                sheet.title = SCORE_SHEET
            return sheet
        if workbook.sheetnames:
            workbook[workbook.sheetnames[0]].title = SCORE_SHEET
            return workbook[SCORE_SHEET]
        return workbook.create_sheet(title=SCORE_SHEET)

    def _parse_wear_header(self, value: Any) -> int | None:
        if not isinstance(value, str):
            return None
        if not value.isdigit():
            return None
        return int(value)

    def _wear_columns(self, sheet) -> list[tuple[int, int]]:
        result = []
        for col in range(1, sheet.max_column + 1):
            number = self._parse_wear_header(sheet.cell(1, col).value)
            if number is not None:
                result.append((number, col))
        result.sort(key=lambda item: item[0])
        return result

    def _income_columns(self, sheet) -> list[tuple[int, int]]:
        return self._wear_columns(sheet)

    def _find_column(self, sheet, header: str) -> int | None:
        for col in range(1, sheet.max_column + 1):
            if sheet.cell(1, col).value == header:
                return col
        return None

    def _build_name_row_map(self, sheet, name_col: int) -> dict[str, int]:
        mapping: dict[str, int] = {}
        for row in range(2, sheet.max_row + 1):
            name = sheet.cell(row, name_col).value
            if name:
                mapping[str(name).strip()] = row
        return mapping

    def _ensure_member_rows(
        self,
        sheet,
        name_col: int,
        total_col: int | None,
        value_columns: list[int],
    ) -> dict[str, int]:
        row_map = self._build_name_row_map(sheet, name_col)
        for member in self.get_members():
            name = member["name"]
            if name in row_map:
                continue
            row = sheet.max_row + 1
            for col in value_columns:
                sheet.cell(row, col, 0)
            if total_col is not None:
                sheet.cell(row, total_col, 0)
            sheet.cell(row, name_col, name)
            row_map[name] = row
        return row_map

    def _meta_to_date_map(self, workbook, sheet_name: str) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for date_text, col_name in self._read_sheet_meta(workbook, sheet_name):
            if str(col_name).isdigit():
                mapping[int(col_name)] = str(date_text)
        return mapping

    def _ensure_summary_columns(self, sheet, total_header: str, name_header: str) -> tuple[int, int, bool]:
        changed = False
        total_col = self._find_column(sheet, total_header)
        name_col = self._find_column(sheet, name_header)
        if total_col is None:
            sheet.cell(1, sheet.max_column + 1, total_header)
            changed = True
        if name_col is None:
            sheet.cell(1, sheet.max_column + 1, name_header)
            changed = True

        total_col = self._find_column(sheet, total_header)
        name_col = self._find_column(sheet, name_header)
        assert total_col is not None and name_col is not None

        if name_col != total_col + 1:
            total_values = [sheet.cell(row, total_col).value for row in range(1, sheet.max_row + 1)]
            name_values = [sheet.cell(row, name_col).value for row in range(1, sheet.max_row + 1)]
            for col_index in sorted([total_col, name_col], reverse=True):
                sheet.delete_cols(col_index)
            insert_at = sheet.max_column + 1
            sheet.insert_cols(insert_at, 2)
            for row, value in enumerate(total_values, start=1):
                sheet.cell(row, insert_at, value)
            for row, value in enumerate(name_values, start=1):
                sheet.cell(row, insert_at + 1, value)
            changed = True

        total_col = self._find_column(sheet, total_header)
        name_col = self._find_column(sheet, name_header)
        assert total_col is not None and name_col is not None
        return total_col, name_col, changed

    def _sort_named_rows(self, sheet, total_col: int, name_col: int) -> None:
        rows = []
        for row in range(2, sheet.max_row + 1):
            values = [sheet.cell(row, col).value for col in range(1, sheet.max_column + 1)]
            if values[name_col - 1]:
                rows.append(values)
        rows.sort(
            key=lambda row: (
                -(float(row[total_col - 1]) if isinstance(row[total_col - 1], (int, float)) else 0.0),
                str(row[name_col - 1]),
            )
        )
        for row_index, values in enumerate(rows, start=2):
            for col_index, value in enumerate(values, start=1):
                sheet.cell(row_index, col_index, value)

    def _sort_rows_by_name(self, sheet, name_col: int) -> None:
        rows = []
        for row in range(2, sheet.max_row + 1):
            values = [sheet.cell(row, col).value for col in range(1, sheet.max_column + 1)]
            if values[name_col - 1]:
                rows.append(values)
        rows.sort(key=lambda row: str(row[name_col - 1]))
        for row_index, values in enumerate(rows, start=2):
            for col_index, value in enumerate(values, start=1):
                sheet.cell(row_index, col_index, value)

    def _parse_d_header(self, value: Any) -> int | None:
        if not isinstance(value, str):
            return None
        normalized = value.replace("旧-", "").replace("鏃?", "")
        if not normalized.startswith("D"):
            return None
        suffix = normalized[1:]
        return int(suffix) if suffix.isdigit() else None

    def _d_columns(self, sheet) -> list[tuple[int, int]]:
        result = []
        for col in range(1, sheet.max_column + 1):
            number = self._parse_d_header(sheet.cell(1, col).value)
            if number is not None:
                result.append((number, col))
        result.sort(key=lambda item: item[0])
        return result

