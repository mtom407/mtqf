import polars as pl


class Loan:

    def __init__(self, notional, maturity, tenor, rate):
        self.notional = notional
        self.maturity = maturity
        self.tenor = tenor
        self.rate = rate

        payments_per_year = 12 // self.tenor
        self.num_payments = self.maturity * payments_per_year

    def emi_flat_rate(self):
        """
        Calculates the equated monthly installmnent (EMI) using the flat-rate method.

        The flat-rate method is defined as EMI = (P + I) / N, where:
            - P is the principal of the loan;
            - I is the total interest payaple, I = P * r * N;
            - N is the total number of monthly payment in a loan.

        In the flat-rate method each interest charge is calculated based on the original
        loan amount, even though the loan balance outstanding is gradually being paid down.
        """
        r = self.rate / 12
        total_interest = self.notional * r * self.num_payments
        emi = (self.notional + total_interest) / self.num_payments

        return round(emi, 2)

    def emi_flat_rate_schedule(self):
        """
        Generates a schedule of interest payments and principal repayments over the
        lifetime of the loan according to the flat-rate method.
        """
        r = self.rate / 12
        single_month_interest = self.notional * r
        emi = self.emi_flat_rate()

        schedule = pl.DataFrame(
            {
                "payment_id": pl.arange(1, self.num_payments + 1, eager=True),
                "emi": emi,
                "interest_contrib": single_month_interest,
                "principal_contrib": emi - single_month_interest,
            }
        )

        return schedule

    def emi_reducing_balance(self):
        """
        Calculates the equated monthly installment (EMI) using the reducing balance method.

        THe reducing balance method is defined as:
            P * (r(1+r)^n) / ((1+r)^n-1), where
                - P is the principal of the loan;
                - r is the monthly payment rate
                - n is the total number of monthly payments.
        """
        r = self.rate / 12

        emi = (
            self.notional
            * (r * (1 + r) ** self.num_payments)
            / ((1 + r) ** self.num_payments - 1)
        )

        return round(emi, 2)

    def emi_reducing_balance_schedule(self):
        """
        Generates a schedule of interest payments and principal repayments over the
        lifetime of the loan according to the reducing balance method.
        """
        r = self.rate / 12
        emi = self.emi_reducing_balance()

        interest_payments = []
        principal_repayments = []
        principal_outstanding = []

        outstanding_notional = self.notional
        for i in range(1, self.num_payments + 1):
            # calculate contribution
            interest_pmt = outstanding_notional * r
            principal_pmt = emi - interest_pmt
            # decrease repaid principal
            outstanding_notional -= principal_pmt
            # save results
            interest_payments.append(interest_pmt)
            principal_repayments.append(principal_pmt)
            principal_outstanding.append(outstanding_notional)

        schedule = pl.DataFrame(
            {
                "payment_id": pl.arange(1, self.num_payments + 1, eager=True),
                "emi": emi,
                "principal_outstanding": principal_outstanding,
                "interest_contrib": interest_payments,
                "principal_contrib": principal_repayments,
            }
        )

        return schedule

    def _emi_reducing_balance_schedule_with_prepayment(self, prepayment_amount=0):
        """
        Generates a schedule of interest payments and principal repayments over the
        lifetime of the loan according to the reducing balance method.
        """
        r = self.rate / 12
        emi = self.emi_reducing_balance() + prepayment_amount

        interest_payments = []
        principal_repayments = []
        principal_outstanding = []

        outstanding_notional = self.notional
        for i in range(1, self.num_payments + 1):
            # calculate contribution
            # we always calculate interest - even if the notional goes down to 0
            # this will be handled automatically
            interest_pmt = outstanding_notional * r

            # if the amount that's left on the loan is lower than EMI then
            # the principal repayment for this period will be equal to the
            # outstanding notional and that's a wrap
            if outstanding_notional < emi:
                principal_pmt = outstanding_notional
                outstanding_notional = 0
            # in other cases, proceed as for the base, non-prepaid case
            else:
                principal_pmt = emi - interest_pmt
                outstanding_notional -= principal_pmt

            # save results
            interest_payments.append(interest_pmt)
            principal_repayments.append(principal_pmt)
            principal_outstanding.append(outstanding_notional)

        schedule = pl.DataFrame(
            {
                "payment_id": pl.arange(1, self.num_payments + 1, eager=True),
                "emi": emi,
                "principal_outstanding": principal_outstanding,
                "interest_contrib": interest_payments,
                "principal_contrib": principal_repayments,
            }
        ).with_columns(
            last_period=pl.when(
                (pl.col("principal_outstanding") == 0)
                & (pl.col("principal_contrib") != 0)
            )
            .then(pl.col("payment_id"))
            .otherwise(None)
        )

        return schedule

    def visualize_schedule(self, schedule):
        """
        Generates a barplot showcasing the contribution of the interest payment and the
        principal repayment portion to each cashflow of the loan.
        """
        trans = schedule.select(pl.all().exclude("emi")).unpivot(
            on=("interest_contrib", "principal_contrib"),
            index=("payment_id"),
            variable_name="interest/principal",
            value_name="payment_amount",
        )

        chart = (
            trans.with_columns(
                Contribution=pl.col("interest/principal").replace(
                    {"interest_contrib": "Interest", "principal_contrib": "Principal"}
                )
            )
            .plot.bar(x="payment_id", y="payment_amount", color="Contribution")
            .properties(
                title="EMI Breakdown by Payment",
                width=800,  # width in pixels
                height=400,  # height in pixels
            )
        )
        return chart

    def eir(self):
        """
        Calculate the effective interest rate based on the loan information.
        """
        eir = (1 + self.rate / self.num_payments) ** self.num_payments - 1
        return eir


from itertools import chain, product

if __name__ == "__main__":

    ##########
    # EMI test
    ##########

    l = Loan(500_000, 10, 1, 0.035)
    print(f"Flat-rate EMI: {l.emi_flat_rate()}")
    print(f"Reducing balance EMI: {l.emi_reducing_balance()}")

    # EMIs consist of contributions of both interest and principal, but the composition
    # of each EMI changes over time, and, at the end of the loan term, the loan will be
    # paid down completely.

    #################################
    # Amortization table & graph test
    #################################

    ll = Loan(100_000, 3, 1, 0.06)
    print(f"Flat-rate EMI: {ll.emi_flat_rate()}")
    print(f"Reducing balance EMI: {ll.emi_reducing_balance()}")

    ll_frs = ll.emi_flat_rate_schedule()
    chart = ll.visualize_schedule(ll_frs)
    chart.save("emi_chart_flr.html")

    ll_rbs = ll.emi_reducing_balance_schedule()
    chart = ll.visualize_schedule(ll_rbs)
    chart.save("emi_chart_rbs.html")

    with pl.Config(tbl_rows=50):
        print(ll_rbs)

    ##########
    # EIR test
    ##########

    # 1% to 5% then 10% to 40% by step of 5%
    stated_interest_rates = chain(range(1, 6), range(10, 45, 5))
    compounding_freqs = (1, 3, 6)
    freq_naming = dict(
        zip(
            (str(i) for i in compounding_freqs),
            # compounding_freqs,
            ("Monthly", "Quarterly", "Semiannual"),
        )
    )

    combos = product(stated_interest_rates, compounding_freqs)

    stated_rates = []
    compounding = []
    eirs = []

    for combo in combos:
        rate, comp = combo
        lll = Loan(1, 1, comp, rate / 100)

        eir = lll.eir()

        stated_rates.append(rate)
        compounding.append(comp)
        eirs.append(eir)

    result = (
        pl.DataFrame(
            {
                "Stated Interest Rate": stated_rates,
                "Compounding": compounding,
                "EIR": eirs,
            }
        )
        .pivot(on="Compounding", index="Stated Interest Rate", values="EIR")
        .rename(freq_naming)
    )

    print(result)

    #################
    # Prepayment test
    #################

    llll = Loan(360_000, 30, 1, 5.875 / 100)

    s_base = llll.emi_flat_rate_schedule()
    s_pre = llll._emi_reducing_balance_schedule_with_prepayment(0)

    s_base_total_interest = s_base.select(pl.col("interest_contrib")).sum()
    print(f"Total interest payments, flat-rate: {s_base_total_interest}")

    s_pre_total_interest = s_pre.select(pl.col("interest_contrib")).sum()
    print(f"Total interest payments, reducing balance: {s_pre_total_interest}")

    with pl.Config(tbl_rows=10):
        print(s_pre)
