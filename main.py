"""
Основной файл FastAPI приложения
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from database import init_demo_data, engine, Base
from routes import router

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Инициализация демо-шаблонов
init_demo_data()

app = FastAPI(
    title="Система автоматической генерации кода",
    description="Веб-приложение для автоматической генерации программного кода",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)