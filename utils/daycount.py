import polars as pl
from datetime import date, datetime
from calendar import isleap


def eoy_date(d):
    return date(d.year, 12, 31)


def boy_date(d):
    return date(d.year, 1, 1)


def argcheck(d: date | datetime) -> date:

    if isinstance(d, date):
        return d
    elif isinstance(d, datetime):
        return d.date()
    else:
        raise TypeError(
            "Expected date information of type `datetime.date` or `datetime.datetime`."
        )


def actact(d1, d2):
    d1, d2 = argcheck(d1), argcheck(d2)

    year_range = range(d1.year + 1, d2.year)
    start_fraction = (
        ((eoy_date(d1) - d1).days + 1) / 366
        if isleap(d1.year)
        else ((eoy_date(d1) - d1).days + 1) / 365
    )
    end_fraction = (
        (d2 - boy_date(d2)).days / 366
        if isleap(d2.year)
        else (d2 - boy_date(d2)).days / 365
    )

    between_yrs = len(year_range)

    return start_fraction + between_yrs + end_fraction


def act360(d1, d2):
    d1, d2 = argcheck(d1), argcheck(d2)
    daydiff = (d2 - d1).days
    return daydiff / 360


def act365(d1, d2):
    d1, d2 = argcheck(d1), argcheck(d2)
    daydiff = (d2 - d1).days
    return daydiff / 365


def thirty360(d1, d2):

    numerator = (
        (d2.year - d1.year) * 360
        + (d2.month - d1.month - 1) * 30
        + max(30 - d1.day, 0)
        + min(d2.day, 30)
    )

    return numerator / 360


if __name__ == "__main__":

    d1 = date(2012, 10, 30)
    d2 = date(2014, 2, 20)
    print(f"act365: {act365(d1, d2)}")
    print(f"act360: {act360(d1, d2)}")
    print(f"thirty360: {thirty360(d1, d2)}")
    print(f"actact: {actact(d1, d2)}")
