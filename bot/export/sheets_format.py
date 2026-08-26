"""
Google Sheets formatting and chart helpers.

Uses Sheets API v4 via gspread's spreadsheet.batch_update() —
no additional dependencies beyond gspread.

Column indices are 0-based, row indices are 0-based, end indices are EXCLUSIVE.
"""

from __future__ import annotations

from typing import Any

import gspread


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

def _rgb(r: int, g: int, b: int) -> dict:
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


HEADER_BG  = _rgb(30,  58, 138)   # deep navy
HEADER_FG  = _rgb(255, 255, 255)  # white
ALT_ROW_BG = _rgb(243, 247, 255)  # very light blue
GREEN_BG   = _rgb(209, 250, 229)  # mint green
RED_BG     = _rgb(254, 213, 213)  # soft red
ORANGE_BG  = _rgb(255, 237, 213)  # soft orange
GOLD_BG    = _rgb(254, 249, 195)  # light yellow
WHITE      = _rgb(255, 255, 255)
BORDER_CLR = _rgb(160, 160, 170)  # neutral grey border


# ---------------------------------------------------------------------------
# Low-level primitives
# ---------------------------------------------------------------------------

def _sheet_id(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> int:
    for ws in spreadsheet.worksheets():
        if ws.title == sheet_name:
            return ws.id
    raise ValueError(f"Sheet '{sheet_name}' not found")


def _range(sid: int, r0: int, r1: int, c0: int, c1: int) -> dict:
    return {"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def _cell_fmt(sid: int, r0: int, r1: int, c0: int, c1: int, fmt: dict) -> dict:
    return {"repeatCell": {
        "range": _range(sid, r0, r1, c0, c1),
        "cell": {"userEnteredFormat": fmt},
        "fields": "userEnteredFormat(" + ",".join(fmt.keys()) + ")",
    }}


def _col_width(sid: int, col: int, px: int) -> dict:
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS",
                  "startIndex": col, "endIndex": col + 1},
        "properties": {"pixelSize": px},
        "fields": "pixelSize",
    }}


def _row_height(sid: int, r0: int, r1: int, px: int) -> dict:
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "ROWS",
                  "startIndex": r0, "endIndex": r1},
        "properties": {"pixelSize": px},
        "fields": "pixelSize",
    }}


def _freeze(sid: int, rows: int = 1, cols: int = 0) -> dict:
    return {"updateSheetProperties": {
        "properties": {
            "sheetId": sid,
            "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols},
        },
        "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
    }}


def _number_fmt(sid: int, r0: int, r1: int, c0: int, c1: int, pattern: str) -> dict:
    return _cell_fmt(sid, r0, r1, c0, c1,
                     {"numberFormat": {"type": "NUMBER", "pattern": pattern}})


def _borders(sid: int, r0: int, r1: int, c0: int, c1: int,
             style: str = "SOLID") -> dict:
    b = {"style": style, "width": 1, "color": BORDER_CLR}
    return {"updateBorders": {
        "range": _range(sid, r0, r1, c0, c1),
        "top": b, "bottom": b, "left": b, "right": b,
        "innerHorizontal": b, "innerVertical": b,
    }}


def _cond_gt(sid: int, r0: int, r1: int, c0: int, c1: int,
             threshold: str, bg: dict) -> dict:
    """Conditional: cell > threshold → apply background."""
    return {"addConditionalFormatRule": {
        "rule": {
            "ranges": [_range(sid, r0, r1, c0, c1)],
            "booleanRule": {
                "condition": {"type": "NUMBER_GREATER",
                              "values": [{"userEnteredValue": threshold}]},
                "format": {"backgroundColor": bg},
            },
        },
        "index": 0,
    }}


def _cond_lt(sid: int, r0: int, r1: int, c0: int, c1: int,
             threshold: str, bg: dict) -> dict:
    """Conditional: cell < threshold → apply background."""
    return {"addConditionalFormatRule": {
        "rule": {
            "ranges": [_range(sid, r0, r1, c0, c1)],
            "booleanRule": {
                "condition": {"type": "NUMBER_LESS",
                              "values": [{"userEnteredValue": threshold}]},
                "format": {"backgroundColor": bg},
            },
        },
        "index": 1,
    }}


def _header(sid: int, r0: int, r1: int, c0: int, c1: int, font_size: int = 10) -> dict:
    return _cell_fmt(sid, r0, r1, c0, c1, {
        "backgroundColor": HEADER_BG,
        "textFormat": {"bold": True, "foregroundColor": HEADER_FG, "fontSize": font_size},
        "horizontalAlignment": "CENTER",
    })


# ---------------------------------------------------------------------------
# Транзакции  (A–N, 14 cols)
# Columns:
#   0:Дата  1:Тип  2:Категория  3:Подкатегория  4:Метод
#   5:Сумма₽  6:Stars  7:₽итого  8:Период  9:MRR вклад
#   10:UserID  11:Тариф  12:Реферал  13:Комментарий
# ---------------------------------------------------------------------------

def _fmt_transactions(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_header(sid, 0, 1, 0, 14))
    reqs.append(_row_height(sid, 0, 1, 24))
    # Alternating rows
    for r in range(1, 500, 2):
        reqs.append(_cell_fmt(sid, r, r + 1, 0, 14, {"backgroundColor": ALT_ROW_BG}))
    # ₽ format: col 5 (Сумма₽), 7 (₽итого), 9 (MRR вклад)
    for col in (5, 7, 9):
        reqs.append(_number_fmt(sid, 1, 500, col, col + 1, '#,##0.00" ₽"'))
    # Column widths
    widths = [90, 65, 175, 155, 65, 85, 60, 85, 75, 90, 110, 150, 55, 215]
    for i, w in enumerate(widths):
        reqs.append(_col_width(sid, i, w))
    reqs.append(_freeze(sid, rows=1))
    reqs.append(_borders(sid, 0, 1, 0, 14))  # header border
    return reqs


# ---------------------------------------------------------------------------
# По месяцам  (A–N, 14 cols)
# Columns:
#   0:Месяц  1:Выручка₽  2:Расходы₽  3:Прибыль₽  4:Маржа%
#   5:НовыхПлат  6:Отвалилось  7:Churn%  8:MRR
#   9:Инфра₽  10:РефБаланс₽  11:Промо₽  12:Реклама₽  13:Прочее₽
# ---------------------------------------------------------------------------

def _fmt_by_months(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_header(sid, 0, 1, 0, 14))
    reqs.append(_row_height(sid, 0, 1, 24))
    # ₽ columns: B,C,D,I,J,K,L,M,N (1,2,3,8,9,10,11,12,13)
    for col in (1, 2, 3, 8, 9, 10, 11, 12, 13):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '#,##0.00" ₽"'))
    # % columns: E,H (4,7)
    for col in (4, 7):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '0.0"%"'))
    # Integer columns: F,G (5,6) — count, no decimal
    for col in (5, 6):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '#,##0'))
    reqs.append(_col_width(sid, 0, 80))
    for c in range(1, 14):
        reqs.append(_col_width(sid, c, 108))
    reqs.append(_freeze(sid, rows=1, cols=1))
    # Borders on header
    reqs.append(_borders(sid, 0, 1, 0, 14))
    # Conditional: Прибыль (col 3) green if > 0, red if < 0
    reqs.append(_cond_gt(sid, 1, 200, 3, 4, "0", GREEN_BG))
    reqs.append(_cond_lt(sid, 1, 200, 3, 4, "0", RED_BG))
    # Conditional: Маржа (col 4) green > 50, orange 20-50, red < 20
    reqs.append(_cond_gt(sid, 1, 200, 4, 5, "50", GREEN_BG))
    reqs.append(_cond_lt(sid, 1, 200, 4, 5, "20", RED_BG))
    # Conditional: Churn (col 7) green < 5, orange 5-15, red > 15
    reqs.append(_cond_lt(sid, 1, 200, 7, 8, "5", GREEN_BG))
    reqs.append(_cond_gt(sid, 1, 200, 7, 8, "15", RED_BG))
    return reqs


# ---------------------------------------------------------------------------
# Метрики  (A–C, 3 cols)
# ---------------------------------------------------------------------------

def _fmt_metrics(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_header(sid, 0, 1, 0, 3))
    reqs.append(_row_height(sid, 0, 1, 24))
    reqs.append(_col_width(sid, 0, 235))
    reqs.append(_col_width(sid, 1, 130))
    reqs.append(_col_width(sid, 2, 110))
    # Alternating rows
    for row in range(1, 13, 2):
        reqs.append(_cell_fmt(sid, row, row + 1, 0, 3, {"backgroundColor": ALT_ROW_BG}))
    # Borders on data area
    reqs.append(_borders(sid, 0, 13, 0, 3))
    # Bold metric names
    reqs.append(_cell_fmt(sid, 1, 13, 0, 1, {"textFormat": {"bold": True}}))
    reqs.append(_freeze(sid, rows=1))
    return reqs


# ---------------------------------------------------------------------------
# По тарифам  (A–H, 8 cols)
# Columns:
#   0:Тариф  1:Активных  2:Новых за месяц  3:Выручка₽
#   4:Доля%  5:30-дн.   6:60-дн.           7:90-дн.+
# ---------------------------------------------------------------------------

def _fmt_by_tariffs(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_header(sid, 0, 1, 0, 8))          # 8 cols A-H
    reqs.append(_row_height(sid, 0, 1, 24))
    # ₽ format: col 3 ONLY (Выручка ₽)
    reqs.append(_number_fmt(sid, 1, 50, 3, 4, '#,##0.00" ₽"'))
    # % format: col 4 ONLY (Доля %)
    reqs.append(_number_fmt(sid, 1, 50, 4, 5, '0.0"%"'))
    # Integer counts: cols 1,2,5,6,7
    for col in (1, 2, 5, 6, 7):
        reqs.append(_number_fmt(sid, 1, 50, col, col + 1, '#,##0'))
    # Column widths
    reqs.append(_col_width(sid, 0, 175))
    for c in range(1, 8):
        reqs.append(_col_width(sid, c, 115))
    reqs.append(_freeze(sid, rows=1))
    reqs.append(_borders(sid, 0, 1, 0, 8))
    # Alternating rows
    for r in range(1, 30, 2):
        reqs.append(_cell_fmt(sid, r, r + 1, 0, 8, {"backgroundColor": ALT_ROW_BG}))
    # Highlight tariff names bold
    reqs.append(_cell_fmt(sid, 1, 30, 0, 1, {"textFormat": {"bold": True}}))
    return reqs


# ---------------------------------------------------------------------------
# Аналитика  (A–J, 10 cols)
# Columns:
#   0:Месяц  1:Активных конец  2:Рост выручки%  3:Рост активных%
#   4:Retention%  5:ARPU₽  6:LTV прогноз₽  7:Конверсия%
#   8:Новых триалов  9:Новых платящих
# ---------------------------------------------------------------------------

def _fmt_analytics(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_header(sid, 0, 1, 0, 10))
    reqs.append(_row_height(sid, 0, 1, 24))
    # % columns: 2,3,4,7
    for col in (2, 3, 4, 7):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '0.0"%"'))
    # ₽ columns: 5,6
    for col in (5, 6):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '#,##0.00" ₽"'))
    # Integer counts: 1,8,9
    for col in (1, 8, 9):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '#,##0'))
    reqs.append(_col_width(sid, 0, 80))
    for c in range(1, 10):
        reqs.append(_col_width(sid, c, 118))
    reqs.append(_freeze(sid, rows=1, cols=1))
    reqs.append(_borders(sid, 0, 1, 0, 10))
    # Conditional: Revenue growth (col 2) green > 0, red < 0
    reqs.append(_cond_gt(sid, 1, 200, 2, 3, "0", GREEN_BG))
    reqs.append(_cond_lt(sid, 1, 200, 2, 3, "0", RED_BG))
    # Conditional: User growth (col 3) green > 0, red < 0
    reqs.append(_cond_gt(sid, 1, 200, 3, 4, "0", GREEN_BG))
    reqs.append(_cond_lt(sid, 1, 200, 3, 4, "0", RED_BG))
    # Conditional: Retention (col 4) green > 85, orange 70-85, red < 70
    reqs.append(_cond_gt(sid, 1, 200, 4, 5, "85", GREEN_BG))
    reqs.append(_cond_lt(sid, 1, 200, 4, 5, "70", RED_BG))
    return reqs


# ---------------------------------------------------------------------------
# Chart helpers (Sheets API v4 via gspread batch_update)
# ---------------------------------------------------------------------------

def _line_chart(sid: int, title: str, anchor_row: int, anchor_col: int,
                data_rows: int, series_cols: list[int], domain_col: int = 0,
                width: int = 580, height: int = 320) -> dict:
    series = [
        {"series": {"sourceRange": {"sources": [{
            "sheetId": sid, "startRowIndex": 1, "endRowIndex": data_rows,
            "startColumnIndex": c, "endColumnIndex": c + 1,
        }]}}, "targetAxis": "LEFT_AXIS"}
        for c in series_cols
    ]
    return {"addChart": {"chart": {
        "spec": {
            "title": title,
            "basicChart": {
                "chartType": "LINE",
                "legendPosition": "BOTTOM_LEGEND",
                "axis": [{"position": "BOTTOM_AXIS"}, {"position": "LEFT_AXIS"}],
                "domains": [{"domain": {"sourceRange": {"sources": [{
                    "sheetId": sid, "startRowIndex": 1, "endRowIndex": data_rows,
                    "startColumnIndex": domain_col, "endColumnIndex": domain_col + 1,
                }]}}}],
                "series": series, "headerCount": 1,
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": anchor_row, "columnIndex": anchor_col},
            "widthPixels": width, "heightPixels": height,
        }},
    }}}


def _bar_chart(sid: int, title: str, anchor_row: int, anchor_col: int,
               data_rows: int, series_cols: list[int], domain_col: int = 0) -> dict:
    req = _line_chart(sid, title, anchor_row, anchor_col, data_rows, series_cols, domain_col)
    req["addChart"]["chart"]["spec"]["basicChart"]["chartType"] = "COLUMN"
    return req


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def apply_all_formatting(
    spreadsheet: gspread.Spreadsheet,
    sheet_names: list[str],
    row_counts: dict[str, int],
) -> None:
    """
    Apply formatting and charts to all known sheets in one pass.
    sheet_names: sheets that currently exist.
    row_counts:  {sheet_name: number_of_data_rows (excluding header)}
    """
    format_reqs: list[dict] = []
    chart_reqs:  list[dict] = []

    formatters = {
        "Транзакции":  _fmt_transactions,
        "По месяцам":  _fmt_by_months,
        "Метрики":     _fmt_metrics,
        "По тарифам":  _fmt_by_tariffs,
        "Аналитика":   _fmt_analytics,
    }

    for name, fn in formatters.items():
        if name in sheet_names:
            try:
                sid = _sheet_id(spreadsheet, name)
                format_reqs.extend(fn(sid))
            except Exception:
                pass

    # Charts — По месяцам
    if "По месяцам" in sheet_names:
        try:
            sid = _sheet_id(spreadsheet, "По месяцам")
            n = min(row_counts.get("По месяцам", 25) + 1, 200)
            chart_reqs.append(_line_chart(sid, "📈 Выручка ₽", 1, 16, n, [1]))
            chart_reqs.append(_line_chart(sid, "💎 MRR ₽", 10, 16, n, [8]))
        except Exception:
            pass

    # Charts — По тарифам
    if "По тарифам" in sheet_names:
        try:
            sid = _sheet_id(spreadsheet, "По тарифам")
            n = min(row_counts.get("По тарифам", 10) + 1, 50)
            chart_reqs.append(_bar_chart(sid, "🗂 Активных по тарифу", 1, 10, n, [1]))
        except Exception:
            pass

    # Charts — Аналитика
    if "Аналитика" in sheet_names:
        try:
            sid = _sheet_id(spreadsheet, "Аналитика")
            n = min(row_counts.get("Аналитика", 25) + 1, 200)
            chart_reqs.append(_line_chart(sid, "📊 Рост выручки/активных %", 1, 12, n, [2, 3]))
            chart_reqs.append(_line_chart(sid, "🔄 Retention %", 10, 12, n, [4]))
        except Exception:
            pass

    if format_reqs:
        try:
            spreadsheet.batch_update({"requests": format_reqs})
        except Exception:
            pass

    if chart_reqs:
        try:
            spreadsheet.batch_update({"requests": chart_reqs})
        except Exception:
            pass  # Charts fail silently if they already exist
