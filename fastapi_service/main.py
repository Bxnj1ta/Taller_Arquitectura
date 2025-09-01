from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import boto3
import io
from decouple import config
from mangum import Mangum   # 👈 Import clave

# 🔑 Credenciales AWS (debes pasarlas como Variables de Entorno en Lambda, no con .env)
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME")
AWS_QUERYSTRING_AUTH = config("AWS_QUERYSTRING_AUTH")


# Inyección de dependencias: permite pasar el cliente S3 como argumento (útil para pruebas y desacoplamiento)
def get_s3_client(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_S3_REGION_NAME
):
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

s3_client = get_s3_client()

app = FastAPI()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), s3_client=s3_client):
    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_STORAGE_BUCKET_NAME,
            file.filename,
            ExtraArgs={"ContentType": file.content_type}
        )
        url = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{file.filename}"
        return {"message": "Archivo subido con éxito", "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import Path
import re

def sanitize_filename(filename: str) -> str:
    # Permitir solo letras, números, guiones, puntos y guion bajo
    return re.sub(r'[^\w\-.]', '_', filename)

@app.get("/download/{filename}")
def download_file(filename: str = Path(..., min_length=1, max_length=200), s3_client=s3_client):
    try:
        safe_filename = sanitize_filename(filename)
        file_stream = io.BytesIO()
        s3_client.download_fileobj(AWS_STORAGE_BUCKET_NAME, safe_filename, file_stream)
        file_stream.seek(0)
        return StreamingResponse(
            file_stream,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# 👇 Handler para AWS Lambda
handler = Mangum(app)
