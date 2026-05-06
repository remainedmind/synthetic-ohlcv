import argparse
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from synthetic_ohlcv.config import DEFAULT_EXPORT_DIR, SyntheticKlinesConfig
from synthetic_ohlcv.controls import control_schema_payload
from synthetic_ohlcv.generator import frame_to_records, make_synthetic_ohlcv_with_metadata
from synthetic_ohlcv.io import save_synthetic_ohlcv

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8100


class PreviewRequest(BaseModel):
    config: SyntheticKlinesConfig = Field(default_factory=SyntheticKlinesConfig)


class SaveRequest(BaseModel):
    config: SyntheticKlinesConfig = Field(default_factory=SyntheticKlinesConfig)
    dataset_name: str = "synthetic_ohlcv"
    output_dir: Path = DEFAULT_EXPORT_DIR
    overwrite: bool = True


def create_app() -> FastAPI:
    app = FastAPI(title="Synthetic Klines Generator", version="0.1.0")
    app.mount(
        "/assets",
        StaticFiles(directory=TEMPLATES_DIR, html=False),
        name="synthetic-klines-assets",
    )

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse((TEMPLATES_DIR / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/default-config")
    async def default_config() -> JSONResponse:
        return JSONResponse({"config": SyntheticKlinesConfig().model_dump(mode="json")})

    @app.get("/api/control-schema")
    async def control_schema() -> JSONResponse:
        return JSONResponse({"groups": control_schema_payload()})

    @app.post("/api/preview")
    async def preview(request: PreviewRequest) -> JSONResponse:
        try:
            frame, metadata = make_synthetic_ohlcv_with_metadata(request.config)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return JSONResponse(
            {
                "rows": frame_to_records(frame),
                "metadata": metadata,
            }
        )

    @app.post("/api/save")
    async def save(request: SaveRequest) -> JSONResponse:
        try:
            result = save_synthetic_ohlcv(
                config=request.config,
                dataset_name=request.dataset_name,
                output_dir=request.output_dir,
                overwrite=request.overwrite,
            )
        except (FileExistsError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return JSONResponse(result.to_payload())

    return app


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    uvicorn.run(create_app(), host=host, port=port)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Synthetic Klines Generator app.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind.")
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
