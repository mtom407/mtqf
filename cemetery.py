import polars as pl


def sofr_things():

    path_to_file = r"C:\\Users\\tvsii\\Downloads\\settlement-prices_20250430.csv"

    df = pl.read_csv(path_to_file)
    print(df.head(10))

    curves = df.select(pl.col("Curve ID").unique().sort())
    with pl.Config(tbl_rows=40):
        print(curves)

    sofr = df.filter(pl.col("Curve ID") == "USD.SOFR.1D", pl.col("Value Type") == "S")
    sofr.write_csv("./data/full_sofr.csv")
    selected_sofr = sofr.select(pl.col("Maturity Offset", "Value"))
    selected_sofr.write_csv("./data/selected_sofr.csv")

    tenors = [
        1,
        2,
        3,
        7,
        14,
        21,
        30,
        60,
        90,
        120,
        150,
        180,
        210,
        240,
        270,
        300,
        330,
        365,
    ] + [i * 365 for i in range(2, 11)]

    sofr_lite = selected_sofr.filter(pl.col("Maturity Offset").is_in(tenors))
    with pl.Config(tbl_rows=50):
        print(sofr_lite)

    sofr_lite.write_csv("./data/sofr_lite.csv")


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
        new_d = date(d.year, d.month + months, month_max_days)
    else:
        if keep_eom:
            new_d = date(d.year, d.month + months, month_max_days)
        else:
            new_d = date(d.year, d.month + months, d.day)

    return new_d
