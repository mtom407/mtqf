import numpy as np
import pandas as pd


def historical_vol(returns: pd.Series) -> float:
    """
    Compute the historical volatility of a time series of returns.

    Parameters:
    returns (pd.Series): A time series of returns.

    Returns:
    float: The standard deviation of the returns, representing historical volatility.
    """
    return returns.std()


# def semi_standard_deviation(returns):
#     n = len(returns) - 1
#     n = (returns - returns.mean() < 0).sum()
#     return np.sqrt(np.sum(np.minimum(returns - returns.mean(), 0) ** 2) / n)


def semi_standard_deviation(returns: pd.Series) -> float:
    """
    Compute the semi-standard deviation (downside deviation) of a time series of returns.

    Semi-standard deviation measures the volatility of negative returns, focusing only on downside risk.

    Parameters:
    returns (pd.Series or np.ndarray): A time series of stock returns.

    Returns:
    float: The semi-standard deviation of the returns.
    """
    # n = len(returns) - 1  # Degrees of freedom: subtracting 1 for sample calculation
    n = (returns - returns.mean() < 0).sum()
    downside_returns = np.minimum(
        returns - returns.mean(), 0
    )  # Keep only negative deviations
    return np.sqrt(np.sum(downside_returns**2) / n)
