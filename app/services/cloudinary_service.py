import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadedImage:
    url: str
    public_id: str


def _ensure_cloudinary_configured() -> tuple[str, str, str]:
    if (
        not settings.CLOUDINARY_CLOUD_NAME
        or not settings.CLOUDINARY_API_KEY
        or not settings.CLOUDINARY_API_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary is not configured.",
        )

    return (
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET,
    )


def _sign_upload_params(params: dict[str, str], api_secret: str) -> str:
    payload = "&".join(f"{key}={value}" for key, value in sorted(params.items()) if value)
    return hashlib.sha1(f"{payload}{api_secret}".encode()).hexdigest()


def _multipart_body(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[bytes, str]:
    boundary = f"----drive-spark-rent-{uuid.uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(value.encode())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode(),
    )
    body.extend(content)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    return bytes(body), boundary


def _upload_to_cloudinary(content: bytes, filename: str, content_type: str) -> UploadedImage:
    cloud_name, api_key, api_secret = _ensure_cloudinary_configured()
    timestamp = str(int(time.time()))
    params = {
        "folder": settings.CLOUDINARY_FOLDER,
        "timestamp": timestamp,
    }
    signature = _sign_upload_params(params, api_secret)
    fields = {
        **params,
        "api_key": api_key,
        "signature": signature,
    }
    body, boundary = _multipart_body(fields, "file", filename, content_type, content)
    request = Request(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="ignore")
        detail = _cloudinary_error_detail(response_body)
        logger.warning(
            "Cloudinary upload failed with status %s: %s",
            exc.code,
            detail,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloudinary upload failed: {detail}",
        ) from exc
    except (TimeoutError, URLError) as exc:
        logger.warning("Cloudinary upload request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloudinary upload request failed: {exc}",
        ) from exc

    url = data.get("secure_url")
    public_id = data.get("public_id")

    if not isinstance(url, str) or not isinstance(public_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudinary returned an invalid upload response.",
        )

    return UploadedImage(url=url, public_id=public_id)


def _cloudinary_error_detail(response_body: str) -> str:
    if not response_body:
        return "Cloudinary returned an empty error response."

    try:
        data = json.loads(response_body)
    except json.JSONDecodeError:
        return response_body

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(data.get("message"), str):
            return data["message"]

    return response_body


async def upload_car_image(file: UploadFile) -> UploadedImage:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are supported.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty.")

    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file must be 10MB or smaller.",
        )

    filename = file.filename or "car-image"
    return await run_in_threadpool(_upload_to_cloudinary, content, filename, file.content_type)
