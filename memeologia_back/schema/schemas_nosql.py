
from typing import Optional, List
from fastapi import HTTPException, UploadFile
from config.database_nosql import db
from config.aws_client import upload_to_s3  # Importar la función para subir a AWS S3
from bson import ObjectId
from datetime import datetime
from config.database_nosql import pwd_context



# Función para subir un meme con AWS S3
async def subir_meme_a_s3(
    usuario_id: str, 
    categoria: str, 
    etiquetas: List[str], 
    archivo: UploadFile
):
    # Validar ID del usuario
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    
    # Validar formato del archivo
    if archivo.content_type not in ["image/jpeg", "image/png", "image/gif"]:
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")

    # Subir el archivo a AWS S3
    try:
        s3_url = upload_to_s3(archivo.file, archivo.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el archivo a S3: {str(e)}")

    # Crear el registro en la base de datos
    meme_data = {
        "usuario_id": ObjectId(usuario_id),
        "url_s3": s3_url,
        "categoria": categoria,
        "etiquetas": etiquetas,
        "fecha_subida": datetime.now(),
        "estado": True  # Por defecto, el meme está activo
    }
    result = db["memes"].insert_one(meme_data)

    return {
        "id": str(result.inserted_id),
        "url_s3": s3_url,
        "mensaje": "Meme subido exitosamente"
    }


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
    return {"message": "Meme creado con éxito", "id": str(result.inserted_id)}