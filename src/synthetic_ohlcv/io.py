import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from synthetic_ohlcv.config import DEFAULT_EXPORT_DIR, SyntheticKlinesConfig
from synthetic_ohlcv.generator import KLINE_COLUMNS, make_synthetic_ohlcv_with_metadata

DATASET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class SaveResult:
    dataset_name: str
    parquet_path: Path
    csv_path: Path
    metadata_path: Path
    metadata: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "parquet_path": str(self.parquet_path),
            "csv_path": str(self.csv_path),
            "metadata_path": str(self.metadata_path),
            "metadata": self.metadata,
        }


def save_synthetic_ohlcv(
    config: SyntheticKlinesConfig,
    dataset_name: str,
    output_dir: Path | str = DEFAULT_EXPORT_DIR,
    overwrite: bool = True,
) -> SaveResult:
    resolved_name = validate_dataset_name(dataset_name)
    frame, metadata = make_synthetic_ohlcv_with_metadata(config)
    return save_frame(
        frame=frame,
        metadata=metadata,
        dataset_name=resolved_name,
        output_dir=output_dir,
        overwrite=overwrite,
    )


def save_frame(
    frame: pl.DataFrame,
    metadata: dict[str, Any],
    dataset_name: str,
    output_dir: Path | str = DEFAULT_EXPORT_DIR,
    overwrite: bool = True,
) -> SaveResult:
    resolved_name = validate_dataset_name(dataset_name)
    resolved_dir = Path(output_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    clean_frame = frame.select(KLINE_COLUMNS)
    parquet_path = resolved_dir / f"{resolved_name}.parquet"
    csv_path = resolved_dir / f"{resolved_name}.csv"
    metadata_path = resolved_dir / f"{resolved_name}.metadata.json"
    targets = (parquet_path, csv_path, metadata_path)
    if not overwrite:
        existing = [path for path in targets if path.exists()]
        if existing:
            existing_paths = [str(path) for path in existing]
            raise FileExistsError(f"dataset files already exist: {existing_paths}")

    clean_frame.write_parquet(parquet_path)
    clean_frame.write_csv(csv_path)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return SaveResult(
        dataset_name=resolved_name,
        parquet_path=parquet_path,
        csv_path=csv_path,
        metadata_path=metadata_path,
        metadata=metadata,
    )


def validate_dataset_name(dataset_name: str) -> str:
    candidate = dataset_name.strip()
    if not DATASET_NAME_PATTERN.fullmatch(candidate):
        raise ValueError(
            "dataset_name must start with an alphanumeric character and contain only "
            "letters, numbers, dots, dashes, and underscores"
        )
    return candidate
