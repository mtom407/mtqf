import polars as pl
import numpy as np
import logging
import os

import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt

from scipy import interpolate
from curves.discount import DiscountCurve


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


class ForwardCurve:

    DATE_COL = "maturity"
    VALUE_COL = "discount_factor"

    DATE_TYPE = pl.Int16
    VALUE_TYPE = pl.Float32

    def __init__(self, dc: DiscountCurve, currency: str = None):

        self.dc = dc
        self.currency = currency
