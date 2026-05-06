import numpy as np
import polars as pl

from synthetic_ohlcv import (
    KLINE_COLUMNS,
    CycleComponent,
    JumpShockConfig,
    MeanReversionConfig,
    RegimeShiftConfig,
    SyntheticKlinesConfig,
    VolatilityClusterConfig,
    make_synthetic_ohlcv,
    make_synthetic_ohlcv_with_metadata,
)
from synthetic_ohlcv.generator import _safe_stat


def assert_valid_klines(frame: pl.DataFrame, rows: int) -> None:
    assert frame.height == rows
    assert tuple(frame.columns) == KLINE_COLUMNS
    assert frame.schema == {
        "timestamp": pl.Int64,
        "open": pl.Float64,
        "high": pl.Float64,
        "low": pl.Float64,
        "close": pl.Float64,
        "volume": pl.Float64,
        "turnover": pl.Float64,
    }
    assert frame["timestamp"].is_sorted()
    assert set(np.diff(frame["timestamp"].to_numpy())) == {900_000}
    assert (frame["high"] >= frame["open"]).all()
    assert (frame["high"] >= frame["close"]).all()
    assert (frame["low"] <= frame["open"]).all()
    assert (frame["low"] <= frame["close"]).all()
    assert (frame["volume"] > 0.0).all()
    assert (frame["turnover"] > 0.0).all()
    assert np.isfinite(frame.select(KLINE_COLUMNS[1:]).to_numpy()).all()


def test_make_synthetic_ohlcv_returns_valid_ohlcv_schema() -> None:
    frame = make_synthetic_ohlcv(SyntheticKlinesConfig(rows=300, seed=7))

    assert_valid_klines(frame, rows=300)


def test_make_synthetic_ohlcv_is_reproducible_for_same_seed() -> None:
    config = SyntheticKlinesConfig(rows=128, seed=123)

    left = make_synthetic_ohlcv(config)
    right = make_synthetic_ohlcv(config)

    assert left.equals(right)


def test_zeroed_components_can_generate_flat_benchmark() -> None:
    config = SyntheticKlinesConfig(
        rows=64,
        base_price=500.0,
        linear_bias=0.0,
        noise_std=0.0,
        gap_noise_std=0.0,
        wick_scale=0.0,
        range_multiplier=0.0,
        volume_noise_std=0.0,
        volume_return_sensitivity=0.0,
        volume_range_sensitivity=0.0,
        volume_volatility_sensitivity=0.0,
        cycles=[],
        regime_shift=RegimeShiftConfig(enabled=False, amplitude=0.0),
        volatility_cluster=VolatilityClusterConfig(enabled=False, strength=0.0),
        jump_shocks=JumpShockConfig(enabled=False, probability=0.0, scale=0.0),
        mean_reversion=MeanReversionConfig(enabled=False, strength=0.0),
    )

    frame, metadata = make_synthetic_ohlcv_with_metadata(config)

    assert np.allclose(frame["open"].to_numpy(), 500.0)
    assert np.allclose(frame["high"].to_numpy(), 500.0)
    assert np.allclose(frame["low"].to_numpy(), 500.0)
    assert np.allclose(frame["close"].to_numpy(), 500.0)
    assert np.allclose(frame["volume"].to_numpy(), 1000.0)
    assert metadata["summary"]["total_return"] == 0.0


def test_multiple_components_generate_finite_market_like_data() -> None:
    config = SyntheticKlinesConfig(
        rows=600,
        seed=99,
        cycles=[
            CycleComponent(kind="sine", amplitude=0.001, period=48),
            CycleComponent(kind="cosine", amplitude=0.0007, period=144, phase=0.5, decay=0.2),
        ],
        regime_shift=RegimeShiftConfig(enabled=True, count=4, amplitude=0.0002),
        volatility_cluster=VolatilityClusterConfig(enabled=True, strength=0.5),
        jump_shocks=JumpShockConfig(enabled=True, probability=0.01, scale=0.003),
        mean_reversion=MeanReversionConfig(enabled=True, strength=0.01, window=72),
    )

    frame, metadata = make_synthetic_ohlcv_with_metadata(config)

    assert_valid_klines(frame, rows=600)
    assert len(metadata["components"]["cycles"]) == 2
    assert metadata["components"]["returns"]["jump_shocks"]["std"] > 0.0
    assert metadata["components"]["volatility_multiplier"]["max"] > 1.0


def test_single_regime_shift_branch_is_supported() -> None:
    frame = make_synthetic_ohlcv(
        SyntheticKlinesConfig(
            rows=96,
            seed=3,
            cycles=[],
            regime_shift=RegimeShiftConfig(enabled=True, count=1, amplitude=0.0001),
        )
    )

    assert_valid_klines(frame, rows=96)


def test_enabled_zero_strength_components_have_no_effect() -> None:
    config = SyntheticKlinesConfig(
        rows=96,
        seed=4,
        cycles=[],
        linear_bias=0.0,
        noise_std=0.0,
        jump_shocks=JumpShockConfig(enabled=True, probability=0.0, scale=0.0),
        volatility_cluster=VolatilityClusterConfig(enabled=True, strength=0.0),
        mean_reversion=MeanReversionConfig(enabled=True, strength=0.0),
    )

    _, metadata = make_synthetic_ohlcv_with_metadata(config)

    assert metadata["components"]["returns"]["jump_shocks"]["sum"] == 0.0
    assert metadata["components"]["returns"]["mean_reversion"]["sum"] == 0.0
    assert metadata["components"]["volatility_multiplier"]["mean"] == 1.0


def test_safe_stat_returns_zero_for_empty_or_nonfinite_values() -> None:
    assert _safe_stat(np.array([np.nan]), "mean") == 0.0
