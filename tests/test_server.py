from importlib import resources
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

import synthetic_ohlcv.server as server
from synthetic_ohlcv import KLINE_COLUMNS
from synthetic_ohlcv.server import DEFAULT_PORT, create_app, main, run_server


def test_index_default_config_and_control_schema_routes() -> None:
    client = TestClient(create_app())

    index = client.get("/")
    defaults = client.get("/api/default-config")
    schema = client.get("/api/control-schema")

    assert index.status_code == 200
    assert "Synthetic Klines Generator" in index.text
    assert "field-hint-wrap" in index.text
    app_js = resources.files("synthetic_ohlcv").joinpath("templates/app.js").read_text()
    assert 'tooltip.role = "tooltip";' in app_js
    assert "aria-expanded" in app_js
    assert defaults.status_code == 200
    assert defaults.json()["config"]["interval_ms"] == 900_000
    assert schema.status_code == 200
    assert schema.json()["groups"][0]["key"] == "dataset_export"


def test_preview_endpoint() -> None:
    client = TestClient(create_app())
    config = {
        "rows": 64,
        "seed": 9,
        "cycles": [{"kind": "sine", "amplitude": 0.001, "period": 32, "phase": 0.0, "decay": 0.0}],
    }

    response = client.post("/api/preview", json={"config": config})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rows"]) == 64
    assert list(payload["rows"][0]) == list(KLINE_COLUMNS)
    assert payload["metadata"]["summary"]["interval_ms"] == 900_000
    assert payload["metadata"]["config"]["rows"] == 64


def test_preview_endpoint_maps_generator_value_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_generation(_config: object) -> object:
        raise ValueError("bad generated data")

    monkeypatch.setattr(server, "make_synthetic_ohlcv_with_metadata", fail_generation)
    client = TestClient(create_app())

    response = client.post("/api/preview", json={"config": {"rows": 16}})

    assert response.status_code == 422
    assert response.json()["detail"] == "bad generated data"


def test_save_endpoint_writes_files(tmp_path: Path) -> None:
    client = TestClient(create_app())
    config = {
        "rows": 48,
        "seed": 10,
        "cycles": [
            {"kind": "cosine", "amplitude": 0.001, "period": 24, "phase": 0.0, "decay": 0.0}
        ],
    }

    response = client.post(
        "/api/save",
        json={
            "config": config,
            "dataset_name": "api_dataset",
            "output_dir": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert Path(payload["parquet_path"]).exists()
    assert Path(payload["csv_path"]).exists()
    assert Path(payload["metadata_path"]).exists()
    assert tuple(pl.read_parquet(payload["parquet_path"]).columns) == KLINE_COLUMNS
    assert payload["metadata"]["config"]["rows"] == 48


def test_save_endpoint_rejects_bad_dataset_name(tmp_path: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/save",
        json={
            "config": {"rows": 16},
            "dataset_name": "../bad",
            "output_dir": str(tmp_path),
        },
    )

    assert response.status_code == 422


def test_run_server_and_main_delegate_to_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_uvicorn_run(app: object, host: str, port: int) -> None:
        calls.append((app.title, host, port))

    monkeypatch.setattr(server.uvicorn, "run", fake_uvicorn_run)
    run_server(host="0.0.0.0", port=9999)

    def fake_run_server(host: str, port: int) -> None:
        calls.append(("main", host, port))

    monkeypatch.setattr(server, "run_server", fake_run_server)
    main([])
    main(["--host", "0.0.0.0", "--port", "8123"])

    assert calls == [
        ("Synthetic Klines Generator", "0.0.0.0", 9999),
        ("main", "127.0.0.1", DEFAULT_PORT),
        ("main", "0.0.0.0", 8123),
    ]
