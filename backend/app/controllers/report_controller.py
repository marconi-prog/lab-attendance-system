from __future__ import annotations

from datetime import timedelta

from app.schemas.report import DailyReportQuery, HistoryQuery, MonthlyReportQuery, ReportQuery
from app.services.report_service import ReportService
from app.utils.clock import local_today
from app.utils.db import page_meta


def _period(query) -> tuple:
    end = query.end_date or local_today()
    start = query.start_date or (end - timedelta(days=29))
    return start, end


def summary(query: ReportQuery):
    start, end = _period(query)
    return ReportService.summary(start, end, query.type)


def daily(query: DailyReportQuery):
    return ReportService.daily(query.day, query.type)


def monthly(query: MonthlyReportQuery):
    return ReportService.monthly(query.month, query.type)


def history(query: HistoryQuery):
    start, end = _period(query)
    rows, total = ReportService.history(start, end, query.type, query.status, query.page, query.per_page)
    return {"items": rows, "meta": page_meta(query.page, query.per_page, total)}
