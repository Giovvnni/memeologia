
import re
from typing import Optional, List
from fastapi import HTTPException
from models.models import Usuario, Meme, Comentario  # Importar modelos
from config.database import db
from bson import ObjectId
from datetime import datetime

def validar_correo(email: str):
    # validar el formato del correo
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron, email):
        raise HTTPException(status_code=400, detail="El correo electrónico no tiene un formato válido")
    
# Función para serializar objetos
def serialize_object(data):
    if isinstance(data, list):
        return [serialize_object(item) for item in data]
    if isinstance(data, dict):
        return {key: serialize_object(value) for key, value in data.items()}
    if isinstance(data, ObjectId):
        return str(data)
    return data

# Función para validar la contraseña
def validar_contraseña(contraseña: str):
    if len(contraseña) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if not re.search("[A-Z]", contraseña):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos una letra mayúscula")
    if not re.search("[0-9]", contraseña):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos un número")

# Función para crear un usuario
async def crear_usuario(nombre: str, email: str, contraseña: str, rol: Optional[str] = "usuario"):
    validar_contraseña(contraseña)
    validar_correo(email)
    usuario_data = {
        "nombre": nombre,
        "email": email,
        "contraseña": contraseña,
        "fecha_registro": datetime.now(),
        "rol": rol
    }
    result = db["usuarios"].insert_one(usuario_data)
    return {"id": str(result.inserted_id)}

# Función para crear un meme
async def crear_meme(usuario_id: str, formato: str, estado: Optional[bool] = False):
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="Usuario ID inválido")
    meme_data = {
        "usuario_id": ObjectId(usuario_id),
        "fecha_subida": datetime.now(),
        "formato": formato,
        "estado": estado
    }
    result = db["memes"].insert_one(meme_data)
    return {"id": str(result.inserted_id)}

# Función para crear un comentario
async def crear_comentario(usuario_id: str, meme_id: str, contenido: str):
    if not ObjectId.is_valid(usuario_id) or not ObjectId.is_valid(meme_id):
        raise HTTPException(status_code=400, detail="ID de usuario o meme inválido")
    comentario_data = {
        "usuario_id": ObjectId(usuario_id),
        "meme_id": ObjectId(meme_id),
        "contenido": contenido,
        "fecha": datetime.now()
    }
    result = db["comentarios"].insert_one(comentario_data)
    return {"id": str(result.inserted_id)}

# Función para listar usuarios
async def listar_usuarios() -> List[dict]:
    usuarios = list(db["usuarios"].find())
    return serialize_object(usuarios)

# Función para listar memes
async def listar_memes() -> List[dict]:
    memes = list(db["memes"].find())
    return serialize_object(memes)

# Función para listar comentarios
async def listar_comentarios() -> List[dict]:
    comentarios = list(db["comentarios"].find())
    return serialize_object(comentarios)

# Función para obtener memes agrupados por ID de usuario
async def obtener_memes_con_usuario() -> List[dict]:
    memes = db["memes"].aggregate([
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "usuario_id",
                "foreignField": "_id",
                "as": "usuario_info"
            }
        },
        {
            "$unwind": "$usuario_info"  # Descompone el array de usuario_info
        },
        {
            "$group": {
                "_id": "$usuario_info._id",  # Agrupar por ID de usuario
                "nombre": {"$first": "$usuario_info.nombre"},  # Tomar el nombre del usuario
                "memes": {"$push": {"_id": "$_id", "formato": "$formato", "estado": "$estado", "fecha_subida": "$fecha_subida"}}  # Crear un array de memes
            }
        },
        {
            "$project": {
                "_id": 1,
                "nombre": 1,
                "memes": 1  # Proyectar los campos deseados
            }
        }
    ])
    return serialize_object(list(memes))

# Función para obtener comentarios agrupados por ID de usuario
async def obtener_comentarios_con_meme_usuario() -> List[dict]:
    comentarios = db["comentarios"].aggregate([
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "usuario_id",
                "foreignField": "_id",
                "as": "usuario_info"
            }
        },
        {
            "$unwind": "$usuario_info"  # Descomponer el array de usuario_info
        },
        {
            "$group": {
                "_id": "$usuario_id",  # Agrupar por usuario_id
                "usuario_id": {"$first": "$usuario_info._id"},  # Obtener el ID del usuario
                "nombre_usuario": {"$first": "$usuario_info.nombre"},  # Obtener el nombre
                "imagen_usuario": {"$first": "$usuario_info.imagen"},  # Obtener la imagen
                "comentarios": {
                    "$push": {
                        "id_comentario": {"$toString": "$_id"},  # Convertir el id del comentario a string
                        "contenido": "$contenido",
                        "fecha": "$fecha",
                        "meme_id": {"$toString": "$meme_id"}  # Convertir meme_id a string si es necesario
                    }
                }
            }
        },
        {
            "$project": {
                "usuario_id": 1,
                "nombre_usuario": 1,
                "imagen_usuario": 1,
                "comentarios": 1,
                "_id": 0
            }
        }
    ])
    return serialize_object(list(comentarios))

# Función para actualizar el nombre de un usuario
async def actualizar_nombre_usuario(usuario_id: str, nuevo_nombre: str):
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    db["usuarios"].update_one({"_id": ObjectId(usuario_id)}, {"$set": {"nombre": nuevo_nombre}})
    return {"mensaje": "Usuario actualizado"}

# Función para actualizar el estado de un meme
async def actualizar_estado_meme(meme_id: str, nuevo_estado: bool):
    if not ObjectId.is_valid(meme_id):
        raise HTTPException(status_code=400, detail="ID de meme inválido")
    db["memes"].update_one({"_id": ObjectId(meme_id)}, {"$set": {"estado": nuevo_estado}})
    return {"mensaje": "Meme actualizado"}

# Función para eliminar un usuario
async def eliminar_usuario(usuario_id: str):
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    db["usuarios"].delete_one({"_id": ObjectId(usuario_id)})
    return {"mensaje": "Usuario eliminado"}

# Función para eliminar un meme
async def eliminar_meme(meme_id: str):
    if not ObjectId.is_valid(meme_id):
        raise HTTPException(status_code=400, detail="ID de meme inválido")
    db["memes"].delete_one({"_id": ObjectId(meme_id)})
    return {"mensaje": "Meme eliminado correctamente"}
