"""Deterministic reporting windows for production KPI contracts."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class PeriodWindow:
    """Inclusive date range used by a production report."""

    key: str
    start_date: date
    end_date: date

    def as_dict(self):
        return {
            "key": self.key,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


def _previous_month_same_day(as_of: date) -> date:
    if as_of.month == 1:
        year, month = as_of.year - 1, 12
    else:
        year, month = as_of.year, as_of.month - 1
    day = min(as_of.day, monthrange(year, month)[1])
    return date(year, month, day)


def build_production_periods(as_of: date) -> dict[str, PeriodWindow]:
    """Build inclusive reporting windows from a source report date.

    ``as_of`` must be the latest validated source report date, not an
    arbitrary client/device timestamp. Database aggregation is intentionally
    outside this helper so the period contract can be tested without writes.
    """
    previous_day = as_of - timedelta(days=1)
    previous_month_date = _previous_month_same_day(as_of)
    previous_year_date = date(
        as_of.year - 1,
        as_of.month,
        min(as_of.day, monthrange(as_of.year - 1, as_of.month)[1]),
    )
    return {
        "today": PeriodWindow("today", as_of, as_of),
        "previous_day": PeriodWindow("previous_day", previous_day, previous_day),
        "month_to_date": PeriodWindow(
            "month_to_date", as_of.replace(day=1), as_of
        ),
        "previous_month_to_date": PeriodWindow(
            "previous_month_to_date",
            previous_month_date.replace(day=1),
            previous_month_date,
        ),
        "year_to_date": PeriodWindow(
            "year_to_date", as_of.replace(month=1, day=1), as_of
        ),
        "previous_year_to_date": PeriodWindow(
            "previous_year_to_date",
            previous_year_date.replace(month=1, day=1),
            previous_year_date,
        ),
    }


def serialize_production_periods(as_of: date, source: str) -> dict:
    periods = build_production_periods(as_of)
    return {
        "as_of_date": as_of.isoformat(),
        "as_of_source": source,
        "periods": {key: window.as_dict() for key, window in periods.items()},
        "business_labels": {
            "sd_hi": {
                "status": "pending_business_confirmation",
                "candidate_period": "month_to_date",
            },
            "sd_bi": {
                "status": "pending_business_confirmation",
                "candidate_period": "year_to_date",
            },
        },
    }
