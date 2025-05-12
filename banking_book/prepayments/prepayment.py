import polars as pl
import numpy as np


class DeterministicPrepaymentGenerator:
    """A class to manage and aggregate prepayments in a loan schedule.

    Attributes:
        DATE_COL (str): The name of the date column in the output DataFrame.
        VALUE_COL (str): The name of the value column in the output DataFrame.
        DATE_TYPE (pl.DataType): The expected Polars data type for dates.
        VALUE_TYPE (pl.DataType): The expected Polars data type for values.
    """

    DATE_COL = "month_no"
    VALUE_COL = "amount"

    DATE_TYPE = pl.Int32
    VALUE_TYPE = pl.Float32

    def __init__(self):
        """Initialize the prepayment registry and counter."""
        self.prepayment_registry = []
        self.PREPAYMENT_COUNTER = 0

        pass

    def add_prepayment(self, info: tuple[int, float]) -> None:
        """Add a single prepayment entry.

        Args:
            info (tuple[int, float]): A tuple containing the month number and the prepayment amount.
        """
        self.prepayment_registry.append(info)
        self.PREPAYMENT_COUNTER += 1

    def load_from_frame(self, df: pl.DataFrame) -> None:
        """Load multiple prepayments from a Polars DataFrame.

        The DataFrame must have exactly two columns, which are cast to the expected date and value types.

        Args:
            df (pl.DataFrame): A Polars DataFrame with two columns: date and amount.

        Raises:
            AssertionError: If the DataFrame does not have exactly two columns.
            TypeError: If column casting to expected types fails.
        """
        df_cols = df.columns
        assert (
            len(df_cols) == 2
        ), "Expected dataframes with two columns - date and value"

        try:

            casted = df.select(
                pl.col(df.columns[0]).cast(self.DATE_TYPE),
                pl.col(df.columns[1]).cast(self.VALUE_TYPE),
            )

            self.prepayment_registry.extend(casted.rows())
        except pl.exceptions.ComputeError as e:
            raise TypeError(f"Column casting failed: {e}")

    def prepayment_schedule(self) -> pl.DataFrame:
        """Generate the aggregated prepayment schedule as a Polars DataFrame.

        Returns:
            pl.DataFrame: A DataFrame with prepayments grouped and summed by month number.
        """
        df = pl.DataFrame(
            self.prepayment_registry,
            orient="row",
            schema=[
                (self.DATE_COL, self.DATE_TYPE),
                (self.VALUE_COL, self.VALUE_TYPE),
            ],
        )

        df = df.group_by(pl.col("month_no")).sum().sort("month_no", descending=False)

        return df


class RandomPrepaymentGenerator:

    DATE_COL = "month_no"
    VALUE_COL = "amount"

    DATE_TYPE = pl.Int32
    VALUE_TYPE = pl.Float32

    def __init__(self):
        self.prepayment_registry = []

    def _add_prepayment(self, info: tuple[int, float]) -> None:
        """Add a single prepayment entry.

        Args:
            info (tuple[int, float]): A tuple containing the month number and the prepayment amount.
        """
        self.prepayment_registry.append(info)

    def simple_random_prepayments(
        self, max_time, amount_bounds, prepayment_pct=None, prepayment_prob=None
    ):

        #################
        # Argument checks
        #################
        assert (
            isinstance(amount_bounds, (tuple, list)) and len(amount_bounds) == 2
        ), "`amount_bounds` must be a tuple or list of length 2"

        # check that it's either prepayment_pct or prepayment_prob but not both
        if (prepayment_pct is None) == (prepayment_prob is None):
            raise ValueError(
                "You must specify exactly one of `prepayment_pct` or `prepayment_prob`."
            )

        ######################
        # Logic implementation
        ######################

        # min and max values of prepayment for a single installment
        min_val, max_val = amount_bounds
        installment_nos = list(range(1, max_time + 1))
        # prepayment_pct represents the percentage of installments with prepayments. For example
        # if prepayment_pct is 0.5 and the loan has 12 installments the function will pick randomly
        # 6 out of 12 months to mark as installments with some amount of prepayment
        if prepayment_pct:

            assert (
                prepayment_pct >= 0 and prepayment_pct <= 1
            ), "`prepayment_pct` must be a float in the range [0; 1]"

            # first, draw months/payment_ids where a prepayment occurs from uniform distribution
            sample_size = int(max_time * prepayment_pct)
            prepayment_occurences = np.random.choice(
                installment_nos, size=sample_size, replace=False
            )

            prepayment_amounts = np.random.uniform(
                low=min_val, high=max_val, size=sample_size
            )

        else:

            assert (
                prepayment_prob >= 0 and prepayment_prob <= 1
            ), "`prepayment_prob` must be a float in the range [0; 1]"
            # otherwise, we make use of prepayment_prob which just represents the probability of the
            # customer to prepay. For example, if prepayment_prob is 0.2 and the loan has 12 installments
            # there is 20% chance that at each installment a prepayment will be made.
            prepayment_occurences = [
                item for item in installment_nos if np.random.rand() < prepayment_prob
            ]
            prepayment_amounts = np.random.uniform(
                low=min_val, high=max_val, size=len(prepayment_occurences)
            )

        for pre_month, pre_amount in zip(prepayment_occurences, prepayment_amounts):
            self._add_prepayment((pre_month, pre_amount))

    def generate_from_distribution(self, time_pdm, amount_pdf):
        pass

    def prepayment_schedule(self) -> pl.DataFrame:
        """Generate the aggregated prepayment schedule as a Polars DataFrame.

        Returns:
            pl.DataFrame: A DataFrame with prepayments grouped and summed by month number.
        """
        df = pl.DataFrame(
            self.prepayment_registry,
            orient="row",
            schema=[
                (self.DATE_COL, self.DATE_TYPE),
                (self.VALUE_COL, self.VALUE_TYPE),
            ],
        )

        df = df.group_by(pl.col("month_no")).sum().sort("month_no", descending=False)

        return df


if __name__ == "__main__":

    my_list = [(1, 2), (2, 3), (4, 5)]

    df = pl.DataFrame(
        my_list,
        orient="row",
        schema=[("month_no_new", pl.Int8), ("amount_new", pl.Float32)],
    )

    print(df.rows())

    pg = DeterministicPrepaymentGenerator()
    pg.add_prepayment((5, 5000))
    pg.load_from_frame(df)
    pg.add_prepayment((1, 3000))
    pg.add_prepayment((6, 100))
    pg.add_prepayment((13, 4200))

    pre_s = pg.prepayment_schedule()
    print(pre_s)

    rg = RandomPrepaymentGenerator()
    rg.simple_random_prepayments(12, (100, 1000), prepayment_pct=0.5)
    pre_s = rg.prepayment_schedule()
    print(pre_s)

    rg = RandomPrepaymentGenerator()
    rg.simple_random_prepayments(12, (100, 1000), prepayment_prob=0.2)
    pre_s = rg.prepayment_schedule()
    print(pre_s)
