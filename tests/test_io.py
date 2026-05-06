import json
from pathlib import Path

import polars as pl
import pytest

from synthetic_ohlcv import KLINE_COLUMNS, SyntheticKlinesConfig, save_synthetic_ohlcv
from synthetic_ohlcv.generator import make_synthetic_ohlcv_with_metadata
from synthetic_ohlcv.io import save_frame, validate_dataset_name


def test_save_synthetic_ohlcv_writes_parquet_csv_and_metadata(tmp_path: Path) -> None:
    result = save_synthetic_ohlcv(
        config=SyntheticKlinesConfig(rows=80, seed=5),
        dataset_name="demo_dataset",
        output_dir=tmp_path,
    )

    assert result.parquet_path.exists()
    assert result.csv_path.exists()
    assert result.metadata_path.exists()
    assert tuple(pl.read_parquet(result.parquet_path).columns) == KLINE_COLUMNS
    assert tuple(pl.read_csv(result.csv_path).columns) == KLINE_COLUMNS
    assert json.loads(result.metadata_path.read_text(encoding="utf-8"))["seed"] == 5
    assert result.to_payload()["dataset_name"] == "demo_dataset"


def test_save_frame_can_reject_overwrite(tmp_path: Path) -> None:
    frame, metadata = make_synthetic_ohlcv_with_metadata(SyntheticKlinesConfig(rows=16))

    save_frame(frame, metadata, "existing", tmp_path, overwrite=False)

    with pytest.raises(FileExistsError, match="already exist"):
        save_frame(frame, metadata, "existing", tmp_path, overwrite=False)


def test_validate_dataset_name_rejects_path_traversal() -> None:
    assert validate_dataset_name("demo.ok-1") == "demo.ok-1"
    with pytest.raises(ValueError, match="dataset_name"):
        validate_dataset_name("../bad")
