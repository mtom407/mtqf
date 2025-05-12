import numpy as np
import pandas as pd


def log_returns(
    ts: pd.Series | pd.DataFrame, clean: bool = True
) -> pd.Series | pd.DataFrame:
    """
    Compute the logarithmic returns of a time series.

    Parameters:
    ts (pd.Series or pd.DataFrame): A time series of prices or values.
    clean (boolean): Boolean value of whether or not to drop NA values

    Returns:
    pd.Series or pd.DataFrame: The log returns of the input time series.
    """
    return np.log(ts).diff().dropna() if clean else np.log(ts).diff()


def pct_returns(
    ts: pd.Series | pd.DataFrame, clean: bool = True
) -> pd.Series | pd.DataFrame:
    """
    Compute the percentage returns of a time series.

    Parameters:
    ts (pd.Series or pd.DataFrame): A time series of prices or values.
    clean (boolean): Boolean value of whether or not to drop NA values

    Returns:
    pd.Series or pd.DataFrame: The percentage change between consecutive observations.
    """
    return ts.pct_change().dropna() if clean else ts.pct_change()


def abs_returns(
    ts: pd.Series | pd.DataFrame, clean: bool = True
) -> pd.Series | pd.DataFrame:
    """
    Compute the absolute returns (differences) of a time series.

    Parameters:
    ts (pd.Series or pd.DataFrame): A time series of prices or values.
    clean (boolean): Boolean value of whether or not to drop NA values

    Returns:
    pd.Series or pd.DataFrame: The absolute difference between consecutive observations.
    """
    return ts.diff().dropna() if clean else ts.diff()
