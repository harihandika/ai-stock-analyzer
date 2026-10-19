import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from pydantic import ValidationError

from app.domain.schemas.analysis import BacktestRequest
from app.worker.backtester import Backtester, prepare_signals


def history(n=130):
    close = 100 + np.sin(np.arange(n) / 3) * 5 + np.arange(n) * 0.03
    return pd.DataFrame(
        {
            "trading_date": pd.bdate_range("2024-01-01", periods=n).date,
            "open": close - 0.2,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": (np.arange(n) * 123 % 1500) + 1000,
        }
    )


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"years": 3, "target_profit_pct": 10, "stop_loss_pct": 5}, (10, 5)),
        ({"target_profit": 0.1, "stop_loss": 0.05}, (10, 5)),
    ],
)
def test_parameter_units(payload, expected):
    parsed = BacktestRequest.model_validate(payload)
    assert (parsed.target_profit_pct, parsed.stop_loss_pct) == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"years": 0},
        {"target_profit_pct": 0},
        {"stop_loss_pct": 11},
        {"target_profit": 10},
        {"target_profit": 0.1, "stop_loss_pct": 5},
        {"unknown": True},
        {"stop_loss_pct": float("nan")},
    ],
)
def test_invalid_or_ambiguous_parameters_rejected(payload):
    with pytest.raises(ValidationError):
        BacktestRequest.model_validate(payload)


def test_trading_signals_never_change_when_future_is_appended():
    frame = history()
    columns = [
        "swing_high",
        "swing_low",
        "confirmed_swing_high_price",
        "confirmed_swing_low_price",
        "bos",
        "choch",
        "is_spring",
        "stopping_volume",
        "bullish_fvg",
    ]
    complete = prepare_signals(frame)
    for stop in (60, 70, 95, 115):
        prefix = prepare_signals(frame.iloc[:stop])
        assert_frame_equal(prefix[columns], complete.iloc[:stop][columns])


def manual(n=60):
    frame = history(n)
    frame[["open", "close"]] = 100.0
    frame["high"], frame["low"] = 150.0, 50.0
    for col in ("is_spring", "stopping_volume", "bullish_fvg", "choch"):
        frame[col] = False
    return frame


def test_entry_and_exit_use_next_open_including_gap():
    engine = Backtester("BBCA.JK", 1, 0.10, 0.05)
    engine.df = manual()
    engine.df.loc[50, ["is_spring", "stopping_volume"]] = True
    engine.df.loc[51, ["open", "close"]] = [110, 115]
    engine.df.loc[52, "close"] = 123
    engine.df.loc[53, "open"] = 90
    engine.run_simulation()
    trade = engine.trades[0]
    assert (trade["buy_price"], trade["sell_price"]) == (110, 90)
    assert trade["exit_reason"] == "TAKE_PROFIT"
    assert trade["status"] == "LOSS"  # A gap can turn a TP decision into a loss.
    assert trade["profit_pct"] == pytest.approx(-18.181818)
    assert engine.get_results_dict()["max_drawdown_pct"] == pytest.approx(26.829268)


def test_drawdown_is_equity_peak_to_trough_and_percent_once():
    engine = Backtester("AAPL", 1)
    engine.equity_curve = [{"equity": n} for n in (100, 120, 90)]
    engine._record_trade("a", "b", 100, 110, "TAKE_PROFIT", 0.10, 1, "technical")
    engine._record_trade("c", "d", 100, 90, "STOP_LOSS", -0.10, 1, "technical")
    result = engine.get_results_dict()
    assert result["max_drawdown_pct"] == 25
    assert result["win_rate_pct"] == 50
    assert result["trades"][0]["profit_pct"] == 10
    assert len(result["trades"]) == 2


def test_open_position_is_closed_at_period_end():
    engine = Backtester("AAPL", 1)
    engine.df = manual()
    engine.df.loc[58, ["is_spring", "stopping_volume"]] = True
    engine.df.loc[59, ["open", "close"]] = [100, 103]
    engine.run_simulation()
    assert engine.trades[0]["exit_reason"] == "END_OF_PERIOD"
    assert engine.trades[0]["profit_pct"] == 3


def test_valid_no_trade_has_same_schema():
    engine = Backtester("AAPL", 1)
    engine.df = manual()
    engine.run_simulation()
    result = engine.get_results_dict()
    assert result["trades"] == []
    assert result["total_trades"] == result["win_rate_pct"] == result["max_drawdown_pct"] == 0
    assert result["effective_parameters"]["target_profit_pct"] == 5
