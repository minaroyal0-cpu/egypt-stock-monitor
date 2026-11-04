import unittest

from src.backtest import moving_average_backtest


def make_bars(closes, opens=None):
    opens = opens or closes
    return [{"symbol": "TEST", "date": f"2025-01-{i+1:02d}", "currency": "EGP",
             "open": opens[i], "close": closes[i]} for i in range(len(closes))]


class BacktestTests(unittest.TestCase):
    def test_signal_executes_no_earlier_than_next_open(self):
        bars = make_bars([10, 9, 8, 9, 11, 12, 13], [10, 9, 8, 9, 50, 12, 13])
        result = moving_average_backtest(bars, initial_cash=1000, fast_window=2,
                                         slow_window=3, commission_rate=0, slippage_rate=0)
        buys = [t for t in result["trades"] if t["side"] == "buy"]
        if buys:
            self.assertGreater(buys[0]["date"], "2025-01-04")
            self.assertEqual(buys[0]["reference_open"], 12)

    def test_commission_and_slippage_reduce_buy_quantity(self):
        bars = make_bars([10, 9, 8, 9, 11, 12, 13, 12, 10, 8, 7])
        free = moving_average_backtest(bars, 1000, 2, 3, 0, 0)
        costly = moving_average_backtest(bars, 1000, 2, 3, 0.01, 0.01)
        self.assertLessEqual(costly["final_equity"], free["final_equity"])
        self.assertLessEqual(costly["trades"][0]["shares"], free["trades"][0]["shares"])

    def test_no_negative_cash(self):
        bars = make_bars([10, 9, 8, 9, 11, 12, 13, 12, 10, 8, 7])
        result = moving_average_backtest(bars, 1000, 2, 3)
        self.assertGreaterEqual(result["cash"], -1e-8)
        self.assertTrue(all(p["cash"] >= -1e-8 for p in result["equity_curve"]))

    def test_final_bar_signal_is_not_executed(self):
        bars = make_bars([10, 9, 8, 9, 11, 12])
        result = moving_average_backtest(bars, 1000, 2, 3, 0, 0)
        self.assertTrue(all(t["date"] != bars[-1]["date"] for t in result["trades"]))

    def test_mixed_currency_rejected(self):
        bars = make_bars([10, 9, 8, 9])
        bars[-1]["currency"] = "USD"
        with self.assertRaises(ValueError):
            moving_average_backtest(bars, fast_window=2, slow_window=3)

    def test_invalid_costs_rejected(self):
        with self.assertRaises(ValueError):
            moving_average_backtest(make_bars([10, 9, 8, 9]), fast_window=2,
                                    slow_window=3, commission_rate=1.0)

    def test_adjusted_prices_preferred(self):
        bars = make_bars([10, 9, 8, 9, 11, 12])
        for bar in bars:
            bar["adjusted_open"] = bar["open"] * 0.5
            bar["adjusted_close"] = bar["close"] * 0.5
        result = moving_average_backtest(bars, fast_window=2, slow_window=3)
        self.assertEqual(result["price_basis"], "adjusted_ohlc")


if __name__ == "__main__":
    unittest.main()
