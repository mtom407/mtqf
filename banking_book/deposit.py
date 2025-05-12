import numpy as np


class Deposit:

    def __init__(self, notional, maturity, rate, compounding=1, type="fixed"):
        self.notional = notional
        self.maturity = maturity
        self.rate = rate
        self.compounding = compounding
        self.type = type

    def _simple_interest(self):
        return self.notional * (1 + self.rate * self.maturity)

    def _compound_interest(self):
        return self.notional * (1 + self.rate / self.compounding) ** (
            self.maturity * self.compounding
        )

    def _continuous_interest(self):
        return self.notional * np.exp(self.r * self.maturity)

    def fv(self, compounding_type="continuous"):

        if compounding_type == "simple":
            result = self._simple_interest()
        elif compounding_type == "continuous":
            result = self._continuous_interest()
        else:
            result = self._compound_interest()

        return result

    def pv(self, discount_curve):
        pass
        # get discount factor from the curve
        df = 1

        # discount the future value
        return self.fv() * df
