import numpy as np


class CoxRossRubinstein:
    """Represents a Cox, Ross & Rubinstein binomial tree."""

    def __init__(
        self, S0, K, sigma, r, q, T, steps, option_type="call", exercise_type="european"
    ):
        self.S0 = S0
        self.K = K
        self.sigma = sigma
        self.r = r
        self.q = q
        self.T = T
        self.M = steps
        self.dt = self.T / self.M

        self.option_type = option_type
        self.exercise_type = exercise_type

        self._calculate_movements()

    def _calculate_movements(self):
        """
        Calculates the up & down movement size using the volatility and time step.
        Also calculates the probability of the up movement.

        Returns
        -------
            None
        """
        self.u = np.exp(self.sigma * np.sqrt(self.dt))
        self.d = 1 / self.u
        self.p = (np.exp((self.r - self.q) * self.dt) - self.d) / (self.u - self.d)

    def _overwrite_movements(self, u, d):
        self.u = u
        self.d = d
        self.p = (np.exp((self.r - self.q) * self.dt) - self.d) / (self.u - self.d)

    def simulate_price_tree(self):
        """
        Function to generate the tree of stock prices

        Returns
        -------
        np.ndarray
            the triangular matrix (upper) for of the price tree.
        """
        dt = self.T / self.M
        up = np.arange(self.M + 1)
        up = np.resize(up, (self.M + 1, self.M + 1))
        down = up.transpose() * 2
        S = self.S0 * np.exp(self.sigma * np.sqrt(dt) * (up - down))
        return np.triu(S)

    def simulate_price_tree_iter(self, u, d):

        # interval
        dt = self.T / self.M

        # movements. If u is not passed as argument it will be calculated
        if u is None:
            u = np.exp(self.sigma * np.sqrt(dt))
        # same with d
        if d is None:
            u = np.exp(-self.sigma * np.sqrt(dt))

        # vector of prices, first price is our starting point
        S = np.zeros((self.M + 1, self.M + 1))
        S[0, 0] = self.S0

        z = 1
        for t in range(1, self.M + 1):
            for i in range(z):
                S[i, t] = S[i, t - 1] * u
                S[i + 1, t] = S[i, t - 1] * d
            z += 1
        return S

    def calculate_payoffs(self, price_tree):
        """
        Function to calculate call option payoff at every node.
        Payoff is calculated as the excess of the stock price over the strike price.

        Returns
        -------
        np.ndarray
            the payoff matrix.
        """
        if self.option_type == "call":
            payoffs = np.maximum(np.triu(price_tree - self.K), 0)
        else:
            payoffs = np.maximum(np.triu(self.K - price_tree), 0)
        return payoffs

    def _grab_up(self, matrix, i, j):
        """
        Returns the up movement value from the position of [i, j].
        `i` represents the row of the matrix, `j` is the column.

        Returns
        -------
        np.float64
            the up movement value.
        """
        up_i = i
        up_j = j + 1
        return matrix[up_i, up_j]

    def _grab_down(self, matrix, i, j):
        """
        Returns the down movement value from the position of [i, j].
        `i` represents the row of the matrix, `j` is the column.

        Returns
        -------
        np.float64
            the up down value.
        """
        down_i = i + 1
        down_j = j + 1
        return matrix[down_i, down_j]

    def calculate_option_values(self, payoffs):
        """
        Calculates the option's fair value at every node of the tree.
        `i` represents the row of the matrix, `j` is the column.

        Parameters
        -------
        payoffs : np.ndarray
            the payoff matrix

        Returns
        -------
        np.ndarray
            matrix representing fair value of the option at every tree node.
        """

        # initialize result object
        result = np.zeros_like(payoffs)
        # for the last column, fair value is equal to the payoff (terminal node)
        result[:, -1] = payoffs[:, -1]

        range_cols = reversed(range(len(payoffs) - 1))
        range_rows = range(len(payoffs) - 1)

        for j in range_cols:
            for i in range_rows:

                # print(f"{i=} | {j=}")

                # for the second to last column we want payoffs
                # because the value of the option will be the payoff
                # at the terminal node
                if j == len(payoffs) - 1:
                    source = payoffs
                # for other columns just take the calculated option value
                else:
                    source = result

                up_poff = self._grab_up(source, i, j)
                down_poff = self._grab_down(source, i, j)

                # print(f"{up_poff=} | {down_poff=}")

                discounted_weighted_payoff_i_j = np.exp(-self.r * self.dt) * (
                    self.p * up_poff + (1 - self.p) * down_poff
                )

                # print(f"{self.p=}")
                # print(f"{discounted_weighted_payoff_i_j=}")

                if self.exercise_type == "american":
                    result[i, j] = max(payoffs[i, j], discounted_weighted_payoff_i_j)
                else:
                    result[i, j] = discounted_weighted_payoff_i_j

        return np.triu(result)

    def present_value(self, verbosity=0):
        """
        Returns the present value of the option.

        Returns
        -------
        np.float64
            present value of the option.
        """
        self.price_tree = self.simulate_price_tree()
        self.payoffs = self.calculate_payoffs(self.price_tree)
        self.values = self.calculate_option_values(self.payoffs)

        self.pv = self.values[0, 0]

        if verbosity:
            with np.printoptions(
                linewidth=np.inf, threshold=np.inf, suppress=True, precision=4
            ):
                scaler = 69
                print("Price tree")
                print("-" * scaler)
                print(self.price_tree)
                print()
                print("Payoffs")
                print("-" * scaler)
                print(self.payoffs)
                print()
                print("Option values")
                print("-" * scaler)
                print(self.values)
                print()
                print("=" * 20, f" Present value of the option is {self.pv.round(2)}")

        return self.pv


class BinomialESOP(CoxRossRubinstein):

    def __init__(
        self,
        S0,
        K,
        sigma,
        r,
        q,
        T,
        steps,
        vesting_period,
        option_type="call",
        exercise_type="european",
    ):
        # initialize the CRR tree
        super().__init__(S0, K, sigma, r, q, T, steps, option_type, exercise_type)

        self.vesting_period = vesting_period

        cumulative_step = np.arange(0, self.M + 1) * self.dt
        self.step_matrix = np.tile(cumulative_step, (self.M + 1, 1))
        self.vesting_mask = self.step_matrix <= self.vesting_period

    def set_turnover_rate(self, tr):
        """
        Set the percentage corresponding to the expectation that the employee
        leaves the company during each time step.

        Parameters
        -------
        tr : float
            the turnover rate per step.

        """
        self.tr = tr

    def set_exercise_probabilities(self, probs):
        self.ex_probs = probs

    def calculate_option_values(self, payoffs):
        """
        Calculates the option's fair value at every node of the tree.
        `i` represents the row of the matrix, `j` is the column.
        This function takes into account the ESOP object's vesting period,
        turnover rate and the exercise probabilities.

        Exercise is not possible during the vesting period. This corresponds to all
        option values being zeroed out before the vesting period elapses.

        The values of the option at the time nodes depend on the exercise probability
        defined by the `self.ex_probs` parameter. They are used to derive the total
        probabilities of exercsie by incorporating the turnover rate.

        Turnover rate contributes to the total probability of exercise. In cases
        where the employee chooses not to exercise the option there is a % chance
        that they leave the company and HAS to exercise in that case. This % chance
        is dicteted by `self.tr`.

        Finally, the total probability of exercise used to derive the value of the
        option at node [i, j] is defined as:
            total_prob = exercise_prob + (1-exercise_prob) * turnover_rate

        Parameters
        -------
        payoffs : np.ndarray
            the payoff matrix

        Returns
        -------
        np.ndarray
            matrix representing fair value of the option at every tree node.
        """

        # mask payoffs so that exercise not possible during vesting
        payoffs[self.vesting_mask] = 0

        # initialize result object
        result = np.zeros_like(payoffs)
        # for the last column, fair value is equal to the payoff (terminal node)
        result[:, -1] = payoffs[:, -1]

        range_cols = reversed(range(len(payoffs) - 1))
        range_rows = range(len(payoffs) - 1)

        for j in range_cols:
            for i in range_rows:

                # print(f"{i=} | {j=}")
                up_poff = self._grab_up(result, i, j)
                down_poff = self._grab_down(result, i, j)

                # print(f"{up_poff=} | {down_poff=}")

                discounted_weighted_payoff_i_j = np.exp(-self.r * self.dt) * (
                    self.p * up_poff + (1 - self.p) * down_poff
                )

                # calculate total probability of exercise
                total_prob = self.ex_probs[i, j] + (1 - self.ex_probs[i, j]) * self.tr

                # calculate option value:
                # IF employee exercises then they get the payoff
                # IF exercise does not happen or is not possible - the discounted future value is taken
                # both these are weighted with probability of exercise.
                option_value_i_j = (
                    total_prob * payoffs[i, j]
                    + (1 - total_prob) * discounted_weighted_payoff_i_j
                )

                # print(f"{self.p=}")
                # print(f"{discounted_weighted_payoff_i_j=}")

                if self.exercise_type == "american":
                    result[i, j] = max(payoffs[i, j], option_value_i_j)
                else:
                    result[i, j] = option_value_i_j

        return np.triu(result)

    def present_value(self, verbosity=0):
        """
        Returns the present value of the ESOP.

        Returns
        -------
        np.float64
            present value of the option.
        """
        self.price_tree = self.simulate_price_tree()
        self.payoffs = self.calculate_payoffs(self.price_tree)
        self.values = self.calculate_option_values(self.payoffs)

        self.pv = self.values[0, 0]

        if verbosity:
            with np.printoptions(
                linewidth=np.inf, threshold=np.inf, suppress=True, precision=4
            ):
                scaler = 69
                print("Price tree")
                print("-" * scaler)
                print(self.price_tree)
                print()
                print("Payoffs")
                print("-" * scaler)
                print(self.payoffs)
                print()
                print("Option values")
                print("-" * scaler)
                print(self.values)
                print()
                print("=" * 20, f" Present value of the option is {self.pv.round(2)}")

        return self.pv


class EnhancedFASB(CoxRossRubinstein):

    def __init__(
        self,
        S0,
        K,
        sigma,
        r,
        q,
        T,
        steps,
        vesting_period,
        exercise_multiplier=1,
        option_type="call",
        exercise_type="european",
    ):
        # initialize the CRR tree
        super().__init__(S0, K, sigma, r, q, T, steps, option_type, exercise_type)

        self.vesting_period = vesting_period

        cumulative_step = np.arange(0, self.M + 1) * self.dt
        self.step_matrix = np.tile(cumulative_step, (self.M + 1, 1))
        self.vesting_mask = self.step_matrix <= self.vesting_period

        self.km = exercise_multiplier

    def set_turnover_rate(self, tr):
        """
        Set the percentage corresponding to the expectation that the employee
        leaves the company during each time step.

        Parameters
        -------
        tr : float
            the turnover rate per step.

        """
        self.tr = tr

    def calculate_option_values(self, payoffs):
        """
        Calculates the option's fair value at every node of the tree.
        `i` represents the row of the matrix, `j` is the column.
        This function takes into account the ESOP object's vesting period,
        turnover rate and the exercise probabilities.

        Exercise is not possible during the vesting period. This corresponds to all
        option values being zeroed out before the vesting period elapses.

        The values of the option at the time nodes depend on the exercise probability
        defined by the `self.ex_probs` parameter. They are used to derive the total
        probabilities of exercsie by incorporating the turnover rate.

        Turnover rate contributes to the total probability of exercise. In cases
        where the employee chooses not to exercise the option there is a % chance
        that they leave the company and HAS to exercise in that case. This % chance
        is dicteted by `self.tr`.

        Finally, the total probability of exercise used to derive the value of the
        option at node [i, j] is defined as:
            total_prob = exercise_prob + (1-exercise_prob) * turnover_rate

        Parameters
        -------
        payoffs : np.ndarray
            the payoff matrix

        Returns
        -------
        np.ndarray
            matrix representing fair value of the option at every tree node.
        """

        # mask payoffs so that exercise not possible during vesting
        payoffs[self.vesting_mask] = 0

        # initialize result object
        result = np.zeros_like(payoffs)
        # for the last column, fair value is equal to the payoff (terminal node)
        result[:, -1] = payoffs[:, -1]

        range_cols = reversed(range(len(payoffs) - 1))
        range_rows = range(len(payoffs) - 1)

        self.helper = np.zeros_like(self.price_tree)

        for j in range_cols:
            for i in range_rows:

                # print(f"{i=} | {j=}")

                up_poff = self._grab_up(result, i, j)
                down_poff = self._grab_down(result, i, j)

                # print(f"{up_poff=} | {down_poff=}")

                discounted_weighted_payoff_i_j = np.exp(-self.r * self.dt) * (
                    self.p * up_poff + (1 - self.p) * down_poff
                )

                # calculate option value:
                # IF employee exercises then they get the payoff
                # IF exercise does not happen or is not possible - the discounted future value is taken
                # both these are weighted with probability of exercise.
                if (
                    self.price_tree[i, j] >= self.km * self.K
                    and self.step_matrix[i, j] > self.vesting_period
                ):
                    self.helper[i, j] = 1
                    option_value_i_j = payoffs[i, j]
                else:
                    option_value_i_j = (
                        self.tr * self.dt * payoffs[i, j]
                        + (1 - self.tr * self.dt) * discounted_weighted_payoff_i_j
                    )

                # print(f"{self.p=}")
                # print(f"{discounted_weighted_payoff_i_j=}")

                if self.exercise_type == "american":
                    result[i, j] = max(payoffs[i, j], option_value_i_j)
                else:
                    result[i, j] = option_value_i_j

        return np.triu(result)

    def present_value(self, verbosity=0):
        """
        Returns the present value of the ESOP.

        Returns
        -------
        np.float64
            present value of the option.
        """
        self.price_tree = self.simulate_price_tree()
        self.payoffs = self.calculate_payoffs(self.price_tree)
        self.values = self.calculate_option_values(self.payoffs)

        self.pv = self.values[0, 0]

        if verbosity:
            with np.printoptions(
                linewidth=np.inf, threshold=np.inf, suppress=True, precision=4
            ):
                scaler = 69
                print("Price tree")
                print("-" * scaler)
                print(self.price_tree)
                print()
                print("Payoffs")
                print("-" * scaler)
                print(self.payoffs)
                print()
                print("Option values")
                print("-" * scaler)
                print(self.values)
                print()
                print("=" * 20, f" Present value of the option is {self.pv.round(2)}")

        return self.pv
