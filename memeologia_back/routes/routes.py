
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from schema.schemas import (
    crear_usuario,
    crear_meme,
    crear_comentario,
    listar_usuarios,
    listar_memes,
    listar_comentarios,
    obtener_memes_con_usuario,
    obtener_comentarios_con_meme_usuario,
    actualizar_nombre_usuario,
    actualizar_estado_meme,
    eliminar_usuario,
    eliminar_meme
)

router = APIRouter()
# Insertar un usuario
@router.post("/insert/usuarios_insert/")
async def insert_usuario(nombre: str, email: str, contraseña: str, rol: Optional[str] = "usuario"):
    return await crear_usuario(nombre, email, contraseña, rol)

# Insertar un meme
@router.post("/insert/memes_insert/")
async def insert_meme(usuario_id: str, formato: str, estado: Optional[bool] = False):
    return await crear_meme(usuario_id, formato, estado)

# Insertar un comentario
@router.post("/insert/comentarios_insert/")
async def insert_comentario(usuario_id: str, meme_id: str, contenido: str):
    return await crear_comentario(usuario_id, meme_id, contenido)

# Listar usuarios
@router.get("/select/usuarios_select/")
async def get_usuarios():
    return await listar_usuarios()

# Listar memes
@router.get("/select/memesselect/")
async def get_memes():
    return await listar_memes()

# Listar comentarios
@router.get("/select/comentarios_select/")
async def get_comentarios():
    return await listar_comentarios()

# Obtener memes con usuario
@router.get("/select_join/memes_user_join/")
async def get_memes_usuario():
    return await obtener_memes_con_usuario()

# Obtener comentarios con meme y usuario
@router.get("/select_join/comentarios_join/")
async def get_comentarios_usuario():
    return await obtener_comentarios_con_meme_usuario()

# Actualizar nombre de usuario
@router.put("/update/usuarios_update/{usuario_id}")
async def update_usuario(usuario_id: str, nuevo_nombre: str):
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    return await actualizar_nombre_usuario(usuario_id, nuevo_nombre)

# Actualizar estado de un meme
@router.put("/update/memes_update/{meme_id}")
async def update_meme(meme_id: str, nuevo_estado: bool):
    if not ObjectId.is_valid(meme_id):
        raise HTTPException(status_code=400, detail="ID de meme inválido")
    return await actualizar_estado_meme(meme_id, nuevo_estado)

# Eliminar un usuario
@router.delete("/delete/usuarios_delete/{usuario_id}")
async def delete_usuario(usuario_id: str):
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    return await eliminar_usuario(usuario_id)

# Eliminar un meme
@router.delete("/delete/meme_delete/{meme_id}")
async def delete_meme(meme_id: str):
    if not ObjectId.is_valid(meme_id):
        raise HTTPException(status_code=400, detail="ID de meme inválido")
    return await eliminar_meme(meme_id)
