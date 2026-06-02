"""
Google Sheets formatting and chart helpers.

All functions accept a gspread Spreadsheet object and issue batch_update
requests through the underlying Sheets API v4 (no extra dependencies —
gspread exposes the raw API via spreadsheet.client.sheet1 or
spreadsheet.batch_update()).
"""

from __future__ import annotations

from typing import Any

import gspread


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

def _rgb(r: int, g: int, b: int) -> dict:
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


HEADER_BG   = _rgb(30,  58, 138)   # deep blue
HEADER_FG   = _rgb(255, 255, 255)  # white
ALT_ROW_BG  = _rgb(239, 246, 255)  # light blue-white
GREEN_BG    = _rgb(220, 252, 231)  # light green
RED_BG      = _rgb(254, 226, 226)  # light red
ORANGE_BG   = _rgb(255, 237, 213)  # light orange
GOLD_BG     = _rgb(254, 249, 195)  # light yellow
NEUTRAL_BG  = _rgb(248, 250, 252)  # very light grey


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _sheet_id(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> int:
    for ws in spreadsheet.worksheets():
        if ws.title == sheet_name:
            return ws.id
    raise ValueError(f"Sheet '{sheet_name}' not found")


def _range(sheet_id: int, start_row: int, end_row: int,
           start_col: int, end_col: int) -> dict:
    return {
        "sheetId": sheet_id,
        "startRowIndex": start_row,
        "endRowIndex": end_row,
        "startColumnIndex": start_col,
        "endColumnIndex": end_col,
    }


def _cell_fmt(sheet_id: int, r0: int, r1: int, c0: int, c1: int,
              fmt: dict) -> dict:
    return {
        "repeatCell": {
            "range": _range(sheet_id, r0, r1, c0, c1),
            "cell": {"userEnteredFormat": fmt},
            "fields": "userEnteredFormat(" + ",".join(fmt.keys()) + ")",
        }
    }


def _col_width(sheet_id: int, col: int, px: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": col,
                "endIndex": col + 1,
            },
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def _freeze(sheet_id: int, rows: int = 1, cols: int = 0) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols},
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    }


def _number_fmt(sheet_id: int, r0: int, r1: int, c0: int, c1: int,
                pattern: str) -> dict:
    return _cell_fmt(sheet_id, r0, r1, c0, c1,
                     {"numberFormat": {"type": "NUMBER", "pattern": pattern}})


# ---------------------------------------------------------------------------
# Per-sheet format recipes
# ---------------------------------------------------------------------------

def _fmt_transactions(sid: int) -> list[dict]:
    reqs: list[dict] = []
    # Header row — dark blue, white bold text
    reqs.append(_cell_fmt(sid, 0, 1, 0, 14, {
        "backgroundColor": HEADER_BG,
        "textFormat": {"bold": True, "foregroundColor": HEADER_FG, "fontSize": 10},
        "horizontalAlignment": "CENTER",
    }))
    # Alternate row shading (rows 2–500, every other)
    reqs.append(_cell_fmt(sid, 1, 500, 0, 14, {
        "backgroundColor": _rgb(255, 255, 255),
    }))
    # Column widths: A=90 B=70 C=180 D=160 E=70 F-J=80 K=110 L=160 M=55 N=220
    widths = [90, 70, 180, 160, 70, 80, 60, 80, 80, 80, 110, 160, 55, 220]
    for i, w in enumerate(widths):
        reqs.append(_col_width(sid, i, w))
    reqs.append(_freeze(sid, rows=1))
    # ₽ format for F, H, J columns (indices 5, 7, 9)
    for col in (5, 7, 9):
        reqs.append(_number_fmt(sid, 1, 500, col, col + 1, '#,##0.00" ₽"'))
    return reqs


def _fmt_by_months(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_cell_fmt(sid, 0, 1, 0, 14, {
        "backgroundColor": HEADER_BG,
        "textFormat": {"bold": True, "foregroundColor": HEADER_FG, "fontSize": 10},
        "horizontalAlignment": "CENTER",
    }))
    # ₽ cols B,C,D,I,J,K,M,N (1,2,3,8,9,10,12,13)
    for col in (1, 2, 3, 8, 9, 10, 12, 13):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '#,##0.00" ₽"'))
    # % cols E,H  (4,7)
    for col in (4, 7):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '0.0"%"'))
    reqs.append(_col_width(sid, 0, 80))
    for c in range(1, 14):
        reqs.append(_col_width(sid, c, 110))
    reqs.append(_freeze(sid, rows=1, cols=1))
    return reqs


def _fmt_metrics(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_cell_fmt(sid, 0, 1, 0, 3, {
        "backgroundColor": HEADER_BG,
        "textFormat": {"bold": True, "foregroundColor": HEADER_FG, "fontSize": 10},
        "horizontalAlignment": "CENTER",
    }))
    # Metric name col A wider
    reqs.append(_col_width(sid, 0, 230))
    reqs.append(_col_width(sid, 1, 120))
    reqs.append(_col_width(sid, 2, 100))
    # Alternate row shading
    for row in range(1, 13, 2):
        reqs.append(_cell_fmt(sid, row, row + 1, 0, 3, {"backgroundColor": ALT_ROW_BG}))
    reqs.append(_freeze(sid, rows=1))
    return reqs


def _fmt_by_tariffs(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_cell_fmt(sid, 0, 1, 0, 7, {
        "backgroundColor": HEADER_BG,
        "textFormat": {"bold": True, "foregroundColor": HEADER_FG, "fontSize": 10},
        "horizontalAlignment": "CENTER",
    }))
    reqs.append(_col_width(sid, 0, 170))
    for c in range(1, 7):
        reqs.append(_col_width(sid, c, 110))
    for col in (2, 3):
        reqs.append(_number_fmt(sid, 1, 50, col, col + 1, '#,##0.00" ₽"'))
    reqs.append(_number_fmt(sid, 1, 50, 6, 7, '0.0"%"'))
    reqs.append(_freeze(sid, rows=1))
    return reqs


def _fmt_analytics(sid: int) -> list[dict]:
    reqs: list[dict] = []
    reqs.append(_cell_fmt(sid, 0, 1, 0, 10, {
        "backgroundColor": HEADER_BG,
        "textFormat": {"bold": True, "foregroundColor": HEADER_FG, "fontSize": 10},
        "horizontalAlignment": "CENTER",
    }))
    reqs.append(_col_width(sid, 0, 80))
    for c in range(1, 10):
        reqs.append(_col_width(sid, c, 115))
    # % format for growth cols
    for col in (2, 3, 4, 5):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '0.0"%"'))
    for col in (6, 7, 8):
        reqs.append(_number_fmt(sid, 1, 200, col, col + 1, '#,##0.00" ₽"'))
    reqs.append(_freeze(sid, rows=1, cols=1))
    return reqs


# ---------------------------------------------------------------------------
# Chart helpers (Sheets API v4 via gspread batch_update)
# ---------------------------------------------------------------------------

def _line_chart_request(
    sid: int,
    title: str,
    anchor_row: int,
    anchor_col: int,
    data_range_rows: int,
    series_cols: list[int],
    domain_col: int = 0,
) -> dict:
    """
    Creates a LINE chart anchored at (anchor_row, anchor_col) in the sheet.
    series_cols: column indices (0-based) for data series.
    domain_col: column used as X axis labels.
    """
    series = [
        {
            "series": {
                "sourceRange": {
                    "sources": [{
                        "sheetId": sid,
                        "startRowIndex": 1,
                        "endRowIndex": data_range_rows,
                        "startColumnIndex": c,
                        "endColumnIndex": c + 1,
                    }]
                }
            },
            "targetAxis": "LEFT_AXIS",
        }
        for c in series_cols
    ]

    return {
        "addChart": {
            "chart": {
                "spec": {
                    "title": title,
                    "basicChart": {
                        "chartType": "LINE",
                        "legendPosition": "BOTTOM_LEGEND",
                        "axis": [
                            {"position": "BOTTOM_AXIS", "title": "Месяц"},
                            {"position": "LEFT_AXIS", "title": ""},
                        ],
                        "domains": [{
                            "domain": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sid,
                                        "startRowIndex": 1,
                                        "endRowIndex": data_range_rows,
                                        "startColumnIndex": domain_col,
                                        "endColumnIndex": domain_col + 1,
                                    }]
                                }
                            }
                        }],
                        "series": series,
                        "headerCount": 1,
                    },
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {
                            "sheetId": sid,
                            "rowIndex": anchor_row,
                            "columnIndex": anchor_col,
                        },
                        "widthPixels": 600,
                        "heightPixels": 350,
                    }
                },
            }
        }
    }


def _bar_chart_request(
    sid: int,
    title: str,
    anchor_row: int,
    anchor_col: int,
    data_range_rows: int,
    series_cols: list[int],
    domain_col: int = 0,
) -> dict:
    req = _line_chart_request(
        sid, title, anchor_row, anchor_col,
        data_range_rows, series_cols, domain_col
    )
    req["addChart"]["chart"]["spec"]["basicChart"]["chartType"] = "BAR"
    return req


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_all_formatting(
    spreadsheet: gspread.Spreadsheet,
    sheet_names: list[str],
    row_counts: dict[str, int],
) -> None:
    """
    Apply formatting to all known sheets in one batch_update call.
    sheet_names: list of sheets that exist in the spreadsheet.
    row_counts: {sheet_name: number_of_data_rows} for chart ranges.
    """
    requests: list[dict] = []
    chart_requests: list[dict] = []

    formatters = {
        "Транзакции": _fmt_transactions,
        "По месяцам": _fmt_by_months,
        "Метрики": _fmt_metrics,
        "По тарифам": _fmt_by_tariffs,
        "Аналитика": _fmt_analytics,
    }

    for name, fn in formatters.items():
        if name in sheet_names:
            try:
                sid = _sheet_id(spreadsheet, name)
                requests.extend(fn(sid))
            except Exception:
                pass

    # Charts on "По месяцам" — revenue and MRR trend
    if "По месяцам" in sheet_names:
        try:
            sid = _sheet_id(spreadsheet, "По месяцам")
            n = row_counts.get("По месяцам", 25)
            # Revenue line chart
            chart_requests.append(
                _line_chart_request(sid, "📈 Выручка ₽", 1, 16, n + 1, [1])
            )
            # MRR line chart
            chart_requests.append(
                _line_chart_request(sid, "💎 MRR ₽", 10, 16, n + 1, [8])
            )
        except Exception:
            pass

    # Tariff bar chart on "По тарифам"
    if "По тарифам" in sheet_names:
        try:
            sid = _sheet_id(spreadsheet, "По тарифам")
            n = row_counts.get("По тарифам", 10)
            chart_requests.append(
                _bar_chart_request(sid, "🗂 Активных по тарифу", 1, 9, n + 1, [1])
            )
        except Exception:
            pass

    # Analytics growth chart
    if "Аналитика" in sheet_names:
        try:
            sid = _sheet_id(spreadsheet, "Аналитика")
            n = row_counts.get("Аналитика", 25)
            chart_requests.append(
                _line_chart_request(sid, "📊 Рост выручки / активных %", 1, 12, n + 1, [2, 3])
            )
        except Exception:
            pass

    if requests:
        spreadsheet.batch_update({"requests": requests})
    if chart_requests:
        try:
            spreadsheet.batch_update({"requests": chart_requests})
        except Exception:
            # Charts may fail if they already exist — not critical
            pass
