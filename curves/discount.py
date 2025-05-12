import polars as pl
import numpy as np
import logging
import os

import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt

from scipy import interpolate


def setup_logger():

    logging.basicConfig(
        level=logging.DEBUG,
        filename="mylog.log",
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # create if  doesn't exist
    logger = logging.getLogger(__name__)
    # handler - how is the info going to be logged?
    handler = logging.FileHandler("test.log")
    # formatter - how the log will look like
    formatter = logging.Formatter(
        "%(asctime)s - %(filename)s - %(levelname)s - %(message)s"
    )

    # chain everything together
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logger()


class DiscountCurve:
    """
    A class for constructing, manipulating, and visualizing discount curves.

    The class supports input from CSV/XLSX files, lists of (maturity, discount_factor) tuples,
    or Polars DataFrames. It builds an internal interpolator for estimating discount factors
    and zero rates at arbitrary maturities. Provides graphing via Altair or Seaborn.

    Attributes:
        DATE_COL (str): Name of the column holding maturity dates.
        VALUE_COL (str): Name of the column holding discount factors.
        DATE_TYPE (pl.DataType): Polars data type for maturity dates.
        VALUE_TYPE (pl.DataType): Polars data type for discount factors.
        currency (str): Optional currency identifier.
        curve (pl.DataFrame): The discount curve data.
        date_nodes (np.ndarray): Maturities from the curve.
        discount_factors (np.ndarray): Corresponding discount factors.
        interp (callable): Interpolator function.
    """

    DATE_COL = "maturity"
    VALUE_COL = "discount_factor"

    DATE_TYPE = pl.Int16
    VALUE_TYPE = pl.Float32

    def __init__(self, curvesource, currency: str = None):
        """
        Initialize the DiscountCurve object.

        Args:
            curvesource (str | list[tuple] | pl.DataFrame): Source of curve data.
                - File path (.csv or .xlsx)
                - List of (maturity, discount factor) tuples
                - Polars DataFrame with two columns
            currency (str, optional): Currency code or label.

        Raises:
            TypeError: If the input type is unsupported.
        """
        self.currency = currency

        # if it is a list check that it is a list of tuples
        if isinstance(curvesource, list):
            curve = self.from_list(curvesource)
        elif isinstance(curvesource, str):
            curve = self.from_file(curvesource)
        elif isinstance(curvesource, pl.DataFrame):
            curve = self.from_frame(curvesource)
        else:
            raise TypeError("Provided discount curve is of unsupported type.")

        self.curve = curve

        # parse curvesource
        self.date_nodes = (
            curve.select(pl.col(self.DATE_COL)).to_numpy().squeeze()
        )  # np.array(curve.index)
        self.discount_factors = (
            curve.select(pl.col(self.VALUE_COL)).to_numpy().squeeze()
        )  # np.array(curve.values)

        logger.debug(
            "Shapes of date_nodes: {}, and discount_factors: {}".format(
                self.date_nodes.shape, self.discount_factors.shape
            ),
        )

        logger.debug(
            "Values of date_nodes: {}, and discount_factors: {}".format(
                self.date_nodes.squeeze(), self.discount_factors.squeeze()
            ),
        )

        # default interpolation technique
        self.interp = interpolate.interp1d(
            self.date_nodes, self.discount_factors, kind="linear"
        )

    def _verify_curve_format(self, curve: pl.DataFrame) -> pl.DataFrame:
        """
        Ensure that the curve DataFrame has exactly two columns with the correct types.

        Args:
            curve (pl.DataFrame): Input discount curve.

        Returns:
            pl.DataFrame: Formatted discount curve.

        Raises:
            TypeError: If column casting fails.
            AssertionError: If the DataFrame doesn't have exactly two columns.
        """
        logging.info("Verifying curve format...")

        cols = curve.columns
        assert len(cols) == 2, "Expected DataFrame with only two columns."

        try:
            curve = curve.select(
                pl.col(curve.columns[0]).cast(self.DATE_TYPE),
                pl.col(curve.columns[1]).cast(self.VALUE_TYPE),
            )

            curve = curve.rename({cols[0]: self.DATE_COL, cols[1]: self.VALUE_COL})

        except pl.exceptions.ComputeError as e:
            curve = None
            raise TypeError(f"Column casting failed: {e}")

        return curve

    def from_file(self, file: str) -> pl.DataFrame:
        """
        Load a discount curve from a CSV or XLSX file.

        Args:
            file (str): File path.

        Returns:
            pl.DataFrame: Loaded and validated discount curve.

        Raises:
            AssertionError: If file extension is unsupported.
        """
        logging.info("Reading discount curve from file...")

        assert file.endswith(
            (".csv", ".xlsx")
        ), "DiscountCurve supports only .csv and .xlsx files"

        try:
            curve = pl.read_csv(file)
            curve = self._verify_curve_format(curve)
        except Exception as e:
            logging.error(
                f"Reading discount curve from file {file} encountered an exception: "
            )
            logging.error(e)
            curve = None

        return curve

    def from_list(self, node_list: list[tuple]) -> pl.DataFrame:
        """
        Construct a discount curve from a list of (maturity, discount_factor) tuples.

        Args:
            node_list (list[tuple]): List of tuples.

        Returns:
            pl.DataFrame: Discount curve.

        Raises:
            ValueError: If list elements are not 2-element tuples.
        """
        logging.info("Reading discount curve from list...")

        integrity_check = all(
            [isinstance(elem, tuple) and len(elem) == 2 for elem in node_list]
        )
        if integrity_check:
            # unpack into two lists
            dates, factors = zip(*node_list)
            dates = list(dates)
            factors = list(factors)

            curve = pl.DataFrame(
                data={self.DATE_COL: dates, self.VALUE_COL: factors},
                schema={self.DATE_COL: self.DATE_TYPE, self.VALUE_COL: self.VALUE_TYPE},
            )

        else:
            raise ValueError(
                "The expected format for discount curve is a list of 2-element tuples."
            )

        return curve

    def from_frame(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Use an existing Polars DataFrame to construct the discount curve.

        Args:
            df (pl.DataFrame): Input DataFrame.

        Returns:
            pl.DataFrame: Formatted discount curve.
        """
        logging.info("Reading discount curve from dataframe...")

        try:
            curve = self._verify_curve_format(df)
        except Exception as e:
            logging.error(
                f"Setting the discount curve from DataFrame encountered an exception: "
            )
            logging.error(e)
            curve = None

        return curve

    def set_interpolator(self, interpolator, **kwargs) -> None:
        """
        Replace the default interpolator with a custom one.

        Args:
            interpolator (callable): An interpolation function like scipy.interpolate.interp1d.
            **kwargs: Additional arguments passed to the interpolator.

        Raises:
            Exception: If interpolation setup fails.
        """
        try:
            self.interp = interpolator(self.date_nodes, self.discount_factors, **kwargs)
        except Exception as e:
            print("Interpolation set up encountered an exception: ")
            print(e)

    def discount_at(self, date: int) -> np.ndarray:
        """
        Interpolate the discount factor at a specific maturity.

        Args:
            date (int): Maturity in days.

        Returns:
            float: Interpolated discount factor.
        """
        logger.info("Interpolating discount factors...")
        return self.interp(date)

    def discounts_at(self, dates: list | np.ndarray) -> np.ndarray:
        """
        Interpolate discount factors at multiple maturities.

        Args:
            dates (list | np.ndarray): List or array of maturities.

        Returns:
            np.ndarray: Discount factors.
        """
        return self.interp(np.array(dates))

    def zero_rate_at(self, maturity: int) -> np.ndarray:
        """
        Compute the continuously compounded zero rate at a given maturity.

        Args:
            maturity (int): Maturity in days.

        Returns:
            float: Zero rate (as decimal).
        """
        logger.info("Calculating zero rates...")
        dfac = self.discount_at(maturity)
        # continuous
        zero_rate = -np.log(dfac) / (maturity / 365)
        # annual
        # zero_rate =  (1/dfac)**(1/maturity) - 1
        # simple
        # zero_rate = (1-dfac)/(dfac*maturity)
        return zero_rate

    def zero_rates_at(self, maturities: list | np.ndarray) -> np.ndarray:
        """
        Compute zero rates for a list or array of maturities.

        Args:
            maturities (list | np.ndarray): Maturities in days.

        Returns:
            np.ndarray: Corresponding zero rates.
        """
        zero_rates = np.array([self.zero_rate_at(mat) for mat in maturities])
        return zero_rates

    def graph(
        self,
        value_shown: str = "discount",
        how: str = "nodes",
    ) -> alt.Chart:
        """
        Visualize the discount curve or zero rate curve using Altair (nodes) or Seaborn (all).

        Args:
            value_shown (str): "discount" or "rate" to control y-axis content.
            how (str): "nodes" to graph at raw nodes, or "all" to show a full line chart.

        Returns:
            alt.Chart | None: Returns an Altair chart when `how="nodes"`. Uses Matplotlib otherwise.

        Raises:
            AssertionError: If arguments are invalid.
        """
        assert how in ["nodes", "all"], "`how` has to be either `nodes` or `all`."

        assert value_shown in [
            "discount",
            "rate",
        ], "`value_shown` has to be either `discount` or `rate`."

        if how == "nodes":
            if value_shown == "discount":

                # Create Altair chart
                chart = (
                    alt.Chart(self.curve.to_pandas())
                    .mark_circle()
                    .encode(
                        x=f"{self.DATE_COL}",
                        y=alt.Y(
                            f"{self.VALUE_COL}", scale=alt.Scale(domain=[0.4, 1.05])
                        ),
                        tooltip=[self.DATE_COL, self.VALUE_COL],
                        color=alt.value("red"),
                    )
                    .properties(
                        title=f"Discount curve {self.currency}", width=900, height=400
                    )
                    .configure_axis(grid=True)
                    .configure_title(fontSize=16, anchor="start")
                    .configure_view(stroke=None)
                )
            else:
                # Create Altair chart
                RATE_COL = "Zero rate"
                curve = self.curve.with_columns(
                    pl.col(self.DATE_COL)
                    .map_elements(self.zero_rate_at)
                    .alias(RATE_COL)
                )

                min_max = curve.select(
                    pl.col(RATE_COL).min().alias("min_v"),
                    pl.col(RATE_COL).max().alias("max_v"),
                )

                min_val = float(min_max[0, "min_v"]) - 1.5 / 100
                max_val = float(min_max[0, "max_v"]) + 0.25 / 100

                print(min_max)

                chart = (
                    alt.Chart(curve.to_pandas())
                    .mark_circle()
                    .encode(
                        x=f"{self.DATE_COL}",
                        y=alt.Y(
                            f"{RATE_COL}", scale=alt.Scale(domain=[min_val, max_val])
                        ),
                        tooltip=[self.DATE_COL, RATE_COL],
                        color=alt.value("red"),
                    )
                    .properties(
                        title=f"Discount curve {self.currency}", width=900, height=400
                    )
                    .configure_axis(grid=True)
                    .configure_title(fontSize=16, anchor="start")
                    .configure_view(stroke=None)
                )

            return chart

        else:

            date_range = np.arange(1, self.date_nodes.max() + 1)
            if value_shown == "discount":
                values = self.discounts_at(date_range)

                sns.lineplot(x=date_range, y=values, color="black")
                sns.scatterplot(x=self.date_nodes, y=self.discount_factors, color="red")
                plt.ylim(bottom=0.4)
                plt.title(f"Discount curve {self.currency}")
                plt.xlabel("Maturity")
                plt.ylabel("Discount factor")
                plt.grid(True)
                plt.show()
            else:
                values = self.zero_rates_at(date_range)
                values_at_nodes = self.zero_rates_at(self.date_nodes)

                max_v = np.max(values_at_nodes)
                min_v = np.min(values_at_nodes)

                sns.lineplot(x=date_range, y=values, color="black")
                sns.scatterplot(x=self.date_nodes, y=values_at_nodes, color="red")
                plt.ylim(bottom=min_v - 1.5 / 100, top=max_v + 0.25 / 100)
                plt.title(f"Discount curve {self.currency}")
                plt.xlabel("Maturity")
                plt.ylabel("Zero rate")
                plt.grid(True)
                plt.show()


if __name__ == "__main__":
    print("Start of the program.")

    cwd = os.getcwd()
    # print(f"{cwd=}")

    file = "./data/sofr_lite.csv"
    frame = pl.read_csv(file)
    sofr_rows = frame.rows()

    manual_rows = [
        (1, 0.999872),
        (2, 0.999537),
        (30, 0.97532),
        (60, 0.934234),
        (90, 0.912311),
        (180, 0.893213),
    ]

    # try:
    print("===================================================")
    print("Reading in discount curve sources")
    dc1 = DiscountCurve(curvesource=file, currency="USD")
    dc2 = DiscountCurve(curvesource=frame)
    dc3 = DiscountCurve(curvesource=sofr_rows)
    print("===================================================")
    # except Exception as e:
    # print(e)

    chart = dc3.graph(how="nodes", value_shown="rate")
    chart.save("curve.html")
