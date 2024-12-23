from datetime import date, datetime
from io import BytesIO
import logging
from typing import List
from fastapi import APIRouter, File, HTTPException, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from config.database_nosql import memes_collection
from bson import ObjectId
from config.aws_client import upload_to_s3
from models.models_nosql import Comentario
from validation.validations import verificar_id
from schema.schemas_nosql import (
    create_access_token,
    get_current_user,
    get_memes_by_usuario,
    subir_meme_a_s3  # Importar la función de subida de memes a S3
)
from models.models_sql import LoginRequest, Usuario, UsuarioCreate, UsuarioOut
from schema.schemas_sql import crear_usuario, login_usuario
from config.database_sql import get_db
from pydantic import BaseModel

router = APIRouter()


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Llamar a la función para verificar las credenciales
    usuario = login_usuario(db, request.email, request.contraseña)
    
    if usuario is None:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    
    # Crear el token JWT
    access_token = create_access_token(data={"usuario_id": usuario.usuario_id})
    
    # Almacenar la información de autenticación
    auth_data = {
        "usuario_id": usuario.usuario_id,
        "access_token": access_token,
        "token_type": "bearer"
    }
    
    # Log para verificar la autenticación
    print(f"Usuario: {usuario.usuario_id}, Token: {access_token}")
    
    # Retornar la información de autenticación
    return auth_data


# Ruta para insertar un usuario
@router.post("/usuarios")
def insert_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    return crear_usuario(db=db, nombre=usuario.nombre, email=usuario.email, contraseña=usuario.contraseña)

# Subir un meme
@router.post("/upload")
async def upload_meme(
    usuario_id: str = Form(...),
    categoria: str = Form(...),
    etiquetas: List[str] = Form(...),
    archivo: UploadFile = Form(...)
):
    """
    Endpoint para subir un meme, validarlo, subirlo a AWS S3
    y registrar la información en la base de datos.
    """
    return await subir_meme_a_s3(usuario_id, categoria, etiquetas, archivo)

# Crea un modelo Pydantic para la respuesta
class UsuarioResponse(BaseModel):
    usuario_id: int
    nombre: str
    foto_perfil: str

    class Config:
        orm_mode = True

@router.post("/api/usuario/{usuario_id}/photo")
async def upload_photo( usuario_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Generar un nombre de archivo único
        filename = f"{usuario_id}_profile_image.jpg"
        
        # Subir el archivo a S3
        image_url =  upload_to_s3(archivo.file, filename)  # Espera la URL asincrónicamente

        # Actualizar la URL en la base de datos
        usuario = db.query(Usuario).filter(Usuario.usuario_id == usuario_id).first()
        print(usuario)
        if usuario:
            usuario.foto_perfil = image_url
            db.commit()
            db.refresh(usuario)
            
            # Devuelve los datos como un diccionario
            return {"foto_perfil": image_url, "usuario_id": usuario.usuario_id, "nombre": usuario.nombre}

        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir la foto: {str(e)}")




# Obtener un usuario y sus memes
@router.get("/api/usuario/{usuario_id}", response_model=UsuarioOut)
async def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    # Obtener solo el nombre y la foto del perfil del usuario desde SQL
    usuario = db.query(Usuario.nombre, Usuario.foto_perfil).filter(Usuario.usuario_id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener los memes desde MongoDB
    memes = get_memes_by_usuario(usuario_id)

    return UsuarioOut(
        nombre=usuario.nombre,
        foto_perfil=usuario.foto_perfil,
        memes=memes
    )

# Obtener memes
@router.get("/memes")
def get_memes(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    skip = (page - 1) * limit
    memes = memes_collection.find().skip(skip).limit(limit)
    memes_list = list(memes)

    memes_with_user_info = []
    for meme in memes_list:
        usuario = db.query(Usuario.nombre, Usuario.foto_perfil).filter(Usuario.usuario_id == meme['usuario_id']).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        memes_with_user_info.append({
            "id": str(meme["_id"]),
            "imageUrl": meme["url_s3"],
            "usuario_id": meme["usuario_id"],
            "usuario_nombre": usuario.nombre,
            "usuario_foto": usuario.foto_perfil,
        })
    return memes_with_user_info


# Ruta para obtener comentarios de un meme
@router.get("/memes/{meme_id}/comments", response_model=List[Comentario])
async def get_comments(meme_id: str):
    meme = memes_collection.find_one({"_id": ObjectId(meme_id)})
    if not meme:
        raise HTTPException(status_code=404, detail="Meme no encontrado")
    
    # Suponiendo que los comentarios están almacenados en el mismo documento del meme
    comments = meme.get("comments", [])
    return comments

# Ruta para agregar un comentario a un meme


@router.post("/memes/{meme_id}/comments", response_model=Comentario)
async def add_comment(meme_id: str, comment: Comentario):
    try:
        meme_object_id = ObjectId(meme_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de meme inválido")

    # Verificar si el meme existe
    meme = memes_collection.find_one({"_id": meme_object_id})
    if not meme:
        raise HTTPException(status_code=404, detail="Meme no encontrado")

    # Crear un comentario
    comment_data = {
        "_id": str(ObjectId()),  # Generar un _id para el comentario
        "usuario_id": comment.usuario_id,
        "meme_id": meme_id,
        "fecha": comment.fecha or datetime.utcnow(),  # Si no se pasa fecha, usamos la fecha actual
        "contenido": comment.contenido
    }

    # Agregar el comentario al array de comentarios
    result = memes_collection.update_one(
        {"_id": meme_object_id},
        {"$push": {"comments": comment_data}}  # Usamos $push para agregar el comentario al array
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="No se pudo agregar el comentario")

    # Retornar el comentario agregado
    return comment_data



@router.post("/like-meme/{meme_id}")
async def like_meme(meme_id: str, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        meme_object_id = ObjectId(meme_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ID de meme inválido: {e}")

    meme = memes_collection.find_one({"_id": meme_object_id})
    if not meme:
        raise HTTPException(status_code=404, detail="Meme no encontrado")

    print("Meme encontrado:", meme)
    print("Usuario actual:", current_user)

    # Verificar que el usuario esté registrado
    verificar_id(current_user.usuario_id, db)

    # Verificar si el usuario ya ha dado like
    if current_user.usuario_id in meme.get("liked_by_users", []):
        # Si el usuario ya ha dado like, quitarlo
        new_like_count = meme.get("likes", 0) - 1
        memes_collection.update_one(
            {"_id": meme_object_id},
            {
                "$set": {"likes": new_like_count},
                "$pull": {"liked_by_users": current_user.usuario_id}
            }
        )
        return {
            "message": "Like eliminado",
            "likes": new_like_count,
            "meme_id": meme_id,
            "liked_by_users": meme.get("liked_by_users", [])
        }
    else:
        # Si el usuario no ha dado like, agregarlo
        new_like_count = meme.get("likes", 0) + 1
        memes_collection.update_one(
            {"_id": meme_object_id},
            {
                "$set": {"likes": new_like_count},
                "$push": {"liked_by_users": current_user.usuario_id}
            }
        )
        return {
            "message": "Like agregado",
            "likes": new_like_count,
            "meme_id": meme_id,
            "liked_by_users": meme.get("liked_by_users", []) + [current_user.usuario_id]
        }



@router.post("/memes/{meme_id}/report")
async def report_meme(
    meme_id: str,
    current_user: Usuario = Depends(get_current_user),  # Verifica si el usuario está logueado
    db: Session = Depends(get_db)
):
    # Verificar si el usuario está logueado
    if not current_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    meme = memes_collection.find_one({"_id": ObjectId(meme_id)})
    if not meme:
        raise HTTPException(status_code=404, detail="Meme no encontrado")
    
    # Incrementar el contador de reportes
    memes_collection.update_one(
        {"_id": ObjectId(meme_id)},
        {"$inc": {"reported_count": 1}}  # Se incrementa el contador de reportes
    )
    
    return {"message": "Meme reportado exitosamente"}


