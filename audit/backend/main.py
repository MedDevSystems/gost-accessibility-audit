# FILE: audit/backend/main.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: FastAPI-приложение: CORS, .env загрузка, sys.path, монтирование API роутера
#   SCOPE: Инициализация FastAPI app, middleware, lifespan
#   DEPENDS: M-AUDIT-API
#   LINKS: M-AUDIT-APP
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   app — FastAPI application instance (точка входа для uvicorn)
# END_MODULE_MAP

# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 — Первоначальная реализация FastAPI app
# END_CHANGE_SUMMARY

from __future__ import annotations

import os
import sys

# START_BLOCK_SYSPATH: Добавление корня проекта в sys.path для импорта gost_a11y
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# END_BLOCK_SYSPATH

# START_BLOCK_DOTENV: Загрузка .env из корня проекта
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())
# END_BLOCK_DOTENV

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from audit.backend.api import router

# START_BLOCK_APP: Создание FastAPI-приложения
app = FastAPI(
    title="ГОСТ A11Y Audit",
    description="Аудит доступности госсайтов по ГОСТ Р 52872-2019 и Приказу Минцифры №953",
    version="1.0.0",
)
# END_BLOCK_APP

# START_BLOCK_CORS: Разрешение запросов от фронтенд dev-сервера
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# END_BLOCK_CORS

# START_BLOCK_MOUNT: Подключение API роутера
app.include_router(router)
# END_BLOCK_MOUNT
