import unittest

from src.risk import daily_returns, historical_risk, portfolio_concentration


class RiskTests(unittest.TestCase):
    def test_daily_returns(self):
        self.assertAlmostEqual(daily_returns([100, 110, 99])[0], 0.10)
        self.assertAlmostEqual(daily_returns([100, 110, 99])[1], -0.10)

    def test_drawdown(self):
        result = historical_risk([100, 120, 90, 110, 100])
        self.assertAlmostEqual(result["max_drawdown"], 0.25)

    def test_historical_tail_losses_are_nonnegative(self):
        result = historical_risk([100, 101, 99, 98, 102, 97, 96, 100])
        self.assertGreaterEqual(result["historical_var"], 0)
        self.assertGreaterEqual(result["historical_cvar"], 0)
        self.assertEqual(result["method"], "historical_simple_returns")

    def test_insufficient_prices_rejected(self):
        with self.assertRaises(ValueError):
            historical_risk([100, 101])

    def test_nonpositive_prices_rejected(self):
        with self.assertRaises(ValueError):
            historical_risk([100, 0, 101])

    def test_non_finite_prices_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    historical_risk([100, bad, 101])

    def test_non_finite_position_values_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    portfolio_concentration({"ABUK": bad})

    def test_empty_position_symbol_rejected(self):
        with self.assertRaises(ValueError):
            portfolio_concentration({"   ": 100})

    def test_portfolio_concentration(self):
        result = portfolio_concentration({"ABUK": 75, "FWRY": 25})
        self.assertAlmostEqual(result["weights"]["ABUK"], 0.75)
        self.assertAlmostEqual(result["herfindahl_index"], 0.625)
        self.assertAlmostEqual(result["effective_number_of_equal_positions"], 1.6)

    def test_zero_portfolio_rejected(self):
        with self.assertRaises(ValueError):
            portfolio_concentration({"ABUK": 0})


if __name__ == "__main__":
    unittest.main()
