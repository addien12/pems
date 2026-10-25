from datetime import date

from app.production_periods import build_production_periods


def test_periods_use_inclusive_month_and_year_windows():
    periods = build_production_periods(date(2026, 10, 16))

    assert periods["today"].start_date == date(2026, 10, 16)
    assert periods["today"].end_date == date(2026, 10, 16)
    assert periods["previous_day"].start_date == date(2026, 10, 15)
    assert periods["month_to_date"].start_date == date(2026, 10, 1)
    assert periods["month_to_date"].end_date == date(2026, 10, 16)
    assert periods["previous_month_to_date"].start_date == date(2026, 9, 1)
    assert periods["previous_month_to_date"].end_date == date(2026, 9, 16)
    assert periods["year_to_date"].start_date == date(2026, 1, 1)
    assert periods["year_to_date"].end_date == date(2026, 10, 16)


def test_previous_month_date_is_clamped_for_shorter_month():
    periods = build_production_periods(date(2026, 3, 31))

    assert periods["previous_month_to_date"].start_date == date(2026, 2, 1)
    assert periods["previous_month_to_date"].end_date == date(2026, 2, 28)


def test_previous_year_date_is_clamped_for_leap_day():
    periods = build_production_periods(date(2024, 2, 29))

    assert periods["previous_year_to_date"].start_date == date(2023, 1, 1)
    assert periods["previous_year_to_date"].end_date == date(2023, 2, 28)
