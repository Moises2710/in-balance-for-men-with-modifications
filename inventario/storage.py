from __future__ import annotations

import io
import mimetypes
import os
import time
from typing import Optional

from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from urllib.parse import quote

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None  # type: ignore


def _guess_content_type(name: str) -> str:
    content_type, _ = mimetypes.guess_type(name)
    return content_type or "application/octet-stream"


@deconstructible
class SupabaseStorage(Storage):
    """
    Backend de almacenamiento para Supabase Storage.

    Variables de entorno requeridas:
      - SUPABASE_URL
      - SUPABASE_KEY (service role o anon con reglas adecuadas)
      - SUPABASE_BUCKET
      - SUPABASE_PUBLIC ("True"/"False", opcional; default True)
      - SUPABASE_SIGNED_URL_EXPIRES (segundos, opcional; default 3600)
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        bucket: Optional[str] = None,
        public: Optional[bool] = None,
        signed_url_expires: Optional[int] = None,
    ) -> None:
        self.supabase_url = url or os.environ.get("SUPABASE_URL", "").strip()
        self.supabase_key = key or os.environ.get("SUPABASE_KEY", "").strip()
        self.bucket = bucket or os.environ.get("SUPABASE_BUCKET", "").strip()
        self.public = (
            public
            if public is not None
            else os.environ.get("SUPABASE_PUBLIC", "True").lower() == "true"
        )
        self.signed_url_expires = int(
            signed_url_expires
            if signed_url_expires is not None
            else os.environ.get("SUPABASE_SIGNED_URL_EXPIRES", 3600)
        )

        if not (self.supabase_url and self.supabase_key and self.bucket):
            raise RuntimeError(
                "SupabaseStorage requiere SUPABASE_URL, SUPABASE_KEY y SUPABASE_BUCKET"
            )

        if create_client is None:
            raise RuntimeError(
                "La librería 'supabase' no está instalada o no pudo importarse"
            )

        self.client = create_client(self.supabase_url, self.supabase_key)
        self._storage = self.client.storage

    # Utilidades
    def _normalize_name(self, name: str) -> str:
        return name.lstrip("/")

    # Métodos requeridos por Storage
    def _open(self, name: str, mode: str = "rb") -> File:
        name = self._normalize_name(name)
        # Descargar bytes reales desde Supabase para soportar procesadores (ImageKit)
        try:
            blob = self._storage.from_(self.bucket).download(name)
            if isinstance(blob, (bytes, bytearray)):
                return File(io.BytesIO(blob), name)
            data = getattr(blob, "data", None)
            if isinstance(data, (bytes, bytearray)):
                return File(io.BytesIO(data), name)
        except Exception:
            pass
        # Fallback: retornar vacío para no romper, aunque los procesadores pueden fallar
        return File(io.BytesIO(b""), name)

    def _save(self, name: str, content: File) -> str:
        name = self._normalize_name(name)

        # Leer todos los bytes
        if hasattr(content, "seek"):
            try:
                content.seek(0)
            except Exception:
                pass
        file_bytes = content.read()
        if isinstance(file_bytes, str):
            file_bytes = file_bytes.encode("utf-8")

        content_type = getattr(getattr(content, "file", None), "content_type", None)
        content_type = content_type or _guess_content_type(name)

        # Usar el nombre exacto que solicita el caller (ImageKit depende de rutas estables)
        upload_path = name

        # Crear marcador .keep para que el UI muestre la carpeta (prefijo)
        try:
            prefix_dir = os.path.dirname(upload_path)
            if prefix_dir:
                keep_path = f"{prefix_dir}/.keep"
                # Subir un archivo vacío como marcador, con upsert para hacerlo idempotente
                self._storage.from_(self.bucket).upload(
                    keep_path,
                    b"keep",
                    {
                        "content-type": "text/plain",
                        "x-upsert": "true",
                    },
                )
        except Exception:
            # No bloquear el guardado si falla la creación del marcador
            pass

        # Subir archivo (API supabase-py v2)
        res = None
        try:
            # Algunos bindings aceptan upsert como kw y opciones en file_options
            res = self._storage.from_(self.bucket).upload(
                upload_path,
                file_bytes,
                file_options={
                    "content-type": content_type,
                },
                upsert=True,
            )
        except TypeError:
            # Compatibilidad con firmas antiguas: opciones en dict de cabeceras
            res = self._storage.from_(self.bucket).upload(
                upload_path,
                file_bytes,
                {
                    "content-type": content_type,
                    "x-upsert": "true",
                },
            )

        # Evaluar respuesta
        # 1) dict con path
        if isinstance(res, dict):
            if res.get("path"):
                return res["path"]
            if res.get("error"):
                raise RuntimeError(f"Supabase upload error: {res['error']}")
        # 2) objeto con data o error
        data = getattr(res, "data", None)
        if isinstance(data, dict) and data.get("path"):
            return data["path"]
        error = getattr(res, "error", None)
        if error:
            raise RuntimeError(f"Supabase upload error: {error}")

        # Si no conocemos el formato, intentar validar existencia; si no existe, lanzar error
        try:
            listed = self._storage.from_(self.bucket).list(path=os.path.dirname(upload_path) or "")
            if any(f.get("name") == os.path.basename(upload_path) for f in listed or []):
                return upload_path
        except Exception:
            pass
        raise RuntimeError("La subida a Supabase no devolvió 'path' ni se pudo verificar el archivo subido.")

    def exists(self, name: str) -> bool:
        name = self._normalize_name(name)
        try:
            files = self._storage.from_(self.bucket).list(path=os.path.dirname(name) or "")
            return any(f.get("name") == os.path.basename(name) for f in files or [])
        except Exception:
            return False

    def delete(self, name: str) -> None:
        name = self._normalize_name(name)
        try:
            self._storage.from_(self.bucket).remove([name])
        except Exception:
            pass

    def url(self, name: str) -> str:
        name = self._normalize_name(name)
        encoded_path = quote(name, safe="/")
        if self.public:
            # URL pública directa
            return f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{encoded_path}"
        # URL firmada temporal
        signed = self._storage.from_(self.bucket).create_signed_url(
            name, self.signed_url_expires
        )
        if isinstance(signed, dict) and signed.get("signedURL"):
            return signed["signedURL"]
        data = getattr(signed, "data", None)
        if isinstance(data, dict) and data.get("signedURL"):
            return data["signedURL"]
        # Fallback a ruta pública (si el bucket no es público, no servirá)
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{encoded_path}"


