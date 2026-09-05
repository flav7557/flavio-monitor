from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .market_service import MarketService
from .websocket_manager import WebSocketManager


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

manager = WebSocketManager()
service = MarketService(settings, manager)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await service.start()
    yield
    await service.stop()


app = FastAPI(title="Market Terminal API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return service.health()


@app.get("/api/markets")
async def markets() -> list[dict]:
    return service.public_markets()


@app.get("/api/candles/{symbol:path}")
async def candles(
    symbol: str,
    timeframe: str = Query("5m"),
    limit: int = Query(300, ge=1, le=500),
) -> dict:
    try:
        rows = await service.candles(symbol, timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="London Strategic Edge unavailable") from exc
    return {"symbol": symbol, "timeframe": timeframe.lower(), "candles": rows}


@app.websocket("/ws/markets")
async def market_stream(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await websocket.send_json(
        {
            "type": "status",
            "connected": bool(service.stream and service.stream.connected),
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
