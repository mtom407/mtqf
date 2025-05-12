import re
import QuantLib as ql
import pandas as pd
import polars as pl
from datetime import date, timedelta
from collections import defaultdict
from rich.console import Console
from rich.table import Table


class HolidayServer:

    COUNTRIES = {
        "US": (
            ql.UnitedStates,
            {
                ql.UnitedStates.FederalReserve: "FederalReserve",
                ql.UnitedStates.GovernmentBond: "GovernmentBond",
                ql.UnitedStates.LiborImpact: "LiborImpact",
                ql.UnitedStates.NERC: "NERC",
                ql.UnitedStates.NYSE: "NYSE",
                ql.UnitedStates.Settlement: "Settlement",
            },
        ),
        "UK": (
            ql.UnitedKingdom,
            {
                ql.UnitedKingdom.Exchange: "Exchange",
                ql.UnitedKingdom.Metals: "Metals",
                ql.UnitedKingdom.Settlement: "Settlement",
            },
        ),
        "Czech": (ql.CzechRepublic, {ql.CzechRepublic.PSE: "PSE"}),
        "Poland": (ql.Poland, {}),
        "France": (
            ql.France,
            {ql.France.Exchange: "Exchange", ql.France.Settlement: "Settlement"},
        ),
        "Germany": (
            ql.Germany,
            {
                ql.Germany.Eurex: "Eurex",
                ql.Germany.FrankfurtStockExchange: "FrankfurtStockExchange",
                ql.Germany.Settlement: "Settlement",
                ql.Germany.Xetra: "Xetra",
            },
        ),
        "Europe": (ql.TARGET, {}),
        "Canada": (
            ql.Canada,
            {ql.Canada.TSX: "TSX", ql.Canada.Settlement: "Settlement"},
        ),
        "Sweden": (ql.Sweden, {}),
        "Japan": (ql.Japan, {}),
    }

    def __init__(self, start, end):

        self.start = self._to_ql_date(start)
        self.end = self._to_ql_date(end)
        self.holidays = self.__generate_holidays()

        self.console = Console()
        self._setup_holiday_index()

    def _to_ql_date(self, d):
        return ql.Date(d.day, d.month, d.year)

    def __generate_holidays(self):

        all_holiday_lists = {}
        for location, calendar_config in self.COUNTRIES.items():

            calendar_parent, market_children = calendar_config

            if market_children:
                for market, market_name in market_children.items():

                    market_holidays = ql.Calendar.holidayList(
                        calendar_parent(market), self.start, self.end
                    )

                    calendar_name = f"{location}({market_name})"
                    all_holiday_lists[calendar_name] = [
                        qld.to_date() for qld in market_holidays
                    ]
            else:
                market_holidays = ql.Calendar.holidayList(
                    calendar_parent(), self.start, self.end
                )
                calendar_name = f"{location}(Settlement)"
                all_holiday_lists[calendar_name] = [
                    qld.to_date() for qld in market_holidays
                ]

        return all_holiday_lists

    def _extract_cal_market(self, s):
        match = re.match(r"^([^\(]+)\(([^)]+)\)$", s)
        return match.groups() if match else None

    def _setup_holiday_index(self):

        keys = self.holidays.keys()
        calendar_market_pairs = [self._extract_cal_market(k) for k in keys]

        # Group by calendar
        # grouped = defaultdict(list)
        # for calendar, market in calendar_market_pairs:
        #     grouped[calendar].append(market)

        table = Table(title="Holiday Calendars")
        table.add_column("Calendar (coutry)", style="cyan")
        table.add_column("Market", style="italic")

        for country, market in calendar_market_pairs:
            table.add_row(country, market)

        self.table = table

    def print(self):
        self.console.print(self.table)

    def get_holidays(self, country, market):
        key = f"{country}({market})"
        return self.holidays.get(key, None)


if __name__ == "__main__":

    hs = HolidayServer(
        start=date.today(), end=date.today() + timedelta(days=12 * 30 * 50)
    )

    hs.print()

    pl_holidays = hs.get_holidays("Poland", "")
