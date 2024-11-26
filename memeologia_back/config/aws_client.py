import boto3
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException

# Configuración del bucket S3
BUCKET_NAME = "nombre-del-bucket"  # Reemplaza con el nombre de tu bucket
REGION = "us-east-1"  # Cambia según la región de tu bucket

def upload_to_s3(file, filename):
    """
    Sube un archivo a AWS S3 y devuelve la URL pública.
    """
    s3 = boto3.client('s3')
    try:
        s3.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": "image/jpeg"}  # Cambiar ContentType según el archivo
        )
        return f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{filename}"
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Error con las credenciales de AWS")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir archivo a S3: {str(e)}")
