from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import boto3
import io

# 🔑 Credenciales AWS
AWS_ACCESS_KEY_ID = "AKIASDHZAEOPQQF53BHO"
AWS_SECRET_ACCESS_KEY = "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"
AWS_STORAGE_BUCKET_NAME = "bucket-arquitectura-software"
AWS_S3_REGION_NAME = "us-east-2"

# Cliente S3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_S3_REGION_NAME,
)

app = FastAPI()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
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


@app.get("/download/{filename}")
def download_file(filename: str):
    try:
        file_stream = io.BytesIO()
        s3_client.download_fileobj(AWS_STORAGE_BUCKET_NAME, filename, file_stream)
        file_stream.seek(0)
        return StreamingResponse(
            file_stream,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
