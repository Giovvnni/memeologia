from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routes.routes import router

app = FastAPI()



origins = [
    "http://localhost:3000",  # Puerto de tu frontend Next.js
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Permitir que estas URLs hagan solicitudes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todas las cabeceras
)
app.include_router(router)
