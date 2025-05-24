import datetime
import re
from calendar import monthrange
from datetime import date, timedelta
from pandas.tseries.offsets import BDay, CustomBusinessDay
from holidays import HolidayServer


def is_weekend(d):
    return d.weekday() in [5, 6]


def is_eom(d):
    delta = timedelta(days=1)
    next_day = d + delta
    return d.month != next_day.month


def get_eom(d, business_day=False, holidays=[]):
    last_day = monthrange(d.year, d.month)[-1]
    eom = date(d.year, d.month, last_day)
    if business_day:
        cday = CustomBusinessDay(holidays=holidays)
        eom = (eom - cday).date()

    return eom


def shift_months(d, months, keep_eom=True):

    new_years = months // 12
    new_months = months % 12

    # get the number of days in the month after shift
    shifted_month_range = monthrange(d.year + new_years, d.month + new_months)
    month_max_days = shifted_month_range[-1]
    # if current date day number is above max allowed then
    # new date will get the max allowed day for that month
    # NOTE: this should only kick in in EOM situations
    if d.day > month_max_days:
        new_d = date(d.year + new_years, d.month + new_months, month_max_days)
    else:

        new_d = date(d.year + new_years, d.month + new_months, d.day)
        if get_eom(d, business_day=True) == d and keep_eom:
            new_d = date(d.year + new_years, d.month + new_months, month_max_days)

        # if keep_eom:
        #     new_d = date(d.year + new_years, d.month + new_months, month_max_days)
        # else:
        #     new_d = date(d.year + new_years, d.month + new_months, d.day)

    return new_d


def parse_period(period):

    def extract_interval(s):
        match = re.search(r"(\D+)$", s)
        return match.group(1) if match else None

    def extract_number(s):
        match = re.match(r"^(\d+)", s)
        return int(match.group(1)) if match else None

    interval = extract_interval(period)
    quantificator = extract_number(period)

    if interval == "Y":
        return 12 * quantificator
    elif interval == "M":
        return quantificator
    else:
        raise ValueError("Error")


def following(d, period, keep_eom=True, holidays=[]):

    period = parse_period(period)
    new_d = shift_months(d, period, keep_eom=keep_eom)

    cday = CustomBusinessDay(holidays=holidays)

    if new_d in holidays or is_weekend(new_d):
        return (new_d + cday).date()
    else:
        return new_d


def preceding(d, period, keep_eom=True, holidays=[]):
    period = parse_period(period)
    new_d = shift_months(d, period, keep_eom=keep_eom)

    cday = CustomBusinessDay(holidays=holidays)

    if new_d in holidays or is_weekend(new_d):
        return (new_d - cday).date()
    else:
        return new_d


def modified_following(d, period, keep_eom=True, holidays=[]):
    period = parse_period(period)
    new_d = shift_months(d, period, keep_eom=keep_eom)

    cday = CustomBusinessDay(holidays=holidays)

    adjusted = new_d
    while is_weekend(adjusted) or adjusted in holidays:
        # adjusted = (adjusted + BDay(1)).date()
        adjusted = (adjusted + cday).date()

    if adjusted.month != new_d.month:
        adjusted = new_d
        while is_weekend(adjusted) or adjusted in holidays:
            # adjusted = (adjusted - BDay(1)).date()
            adjusted = (adjusted - cday).date()

    return adjusted


def modified_preceding(d, period, keep_eom=True, holidays=[]):
    period = parse_period(period)
    new_d = shift_months(d, period, keep_eom=keep_eom)

    cday = CustomBusinessDay(holidays=holidays)

    adjusted = new_d
    while is_weekend(adjusted) or adjusted in holidays:
        # adjusted = (adjusted - BDay(1)).date()
        adjusted = (adjusted - cday).date()

    if adjusted.month != new_d.month:
        adjusted = new_d
        while is_weekend(adjusted) or adjusted in holidays:
            # adjusted = (adjusted + BDay(1)).date()
            adjusted = (adjusted + cday).date()

    return adjusted


def eom_convention(d, period, holidays=[]):
    pass


if __name__ == "__main__":

    d1 = date(2013, 7, 31)
    d2 = date(2013, 8, 31)

    print(following(d1, "1M"))
    print(preceding(d1, "1M"))
    print(modified_following(d1, "1M"))
    print()

    print(modified_preceding(date(2023, 2, 1), "1M"))
    print(preceding(date(2023, 2, 1), "1M"))

    print("cday test")
    d4 = date(2025, 4, 30)
    print(d4)
    hs = HolidayServer(start=date(2025, 1, 1), end=date(2025, 12, 31))
    polish = hs.get_holidays("Poland", "Settlement")
    cday = CustomBusinessDay(holidays=polish)
    print(d4 + 2 * cday)
    print()

    print(shift_months(date(2025, 2, 15), months=1, keep_eom=False))

    print(get_eom(date(2025, 5, 12)))  # 2025-05-31
    print(
        get_eom(date(2025, 5, 12), business_day=True)
    )  # 2025-05-30 or earlier if 30th is holiday/weekend
