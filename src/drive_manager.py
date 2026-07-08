import io
import json
import base64
import os
from pathlib import Path
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

logger = logging.getLogger(__name__)


class GoogleDriveManager:
    def __init__(self):
        creds_b64 = os.getenv("GOOGLE_DRIVE_CREDENTIALS", "")
        if not creds_b64:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS no configurado")

        creds_dict = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
        self.creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        self.service = build("drive", "v3", credentials=self.creds)
        self.root_folder = os.getenv("DRIVE_FOLDER_ID", "")

        if not self.root_folder:
            self.root_folder = self.create_folder("Conciliacion_Comprobantes")

    def create_folder(self, name, parent_id=None):
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        try:
            folder = (
                self.service.files().create(body=metadata, fields="id").execute()
            )
            logger.info(f"Carpeta creada: {name} ({folder.get('id')})")
            return folder.get("id")
        except Exception as e:
            logger.error(f"Error creando carpeta {name}: {e}")
            return None

    def find_folder(self, name, parent_id=None):
        query = (
            f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false"
        )
        if parent_id:
            query += f" and '{parent_id}' in parents"
        try:
            results = (
                self.service.files()
                .list(q=query, fields="files(id, name)", pageSize=10)
                .execute()
            )
            folders = results.get("files", [])
            return folders[0]["id"] if folders else None
        except Exception as e:
            logger.error(f"Error buscando carpeta {name}: {e}")
            return None

    def get_or_create_folder(self, name, parent_id=None):
        fid = self.find_folder(name, parent_id)
        return fid or self.create_folder(name, parent_id)

    def setup_structure(self):
        root = self.get_or_create_folder("Conciliacion_Comprobantes")
        self.root_folder = root
        for path in [
            "Comprobantes",
            "Comprobantes/Pendientes",
            "Comprobantes/Procesados",
            "Extractos_Bancarios",
        ]:
            parent = root
            for part in path.split("/"):
                parent = self.get_or_create_folder(part, parent)
        logger.info("Estructura de carpetas lista en Google Drive")
        return root

    def list_files(self, folder_path, mime_filter=None):
        parts = folder_path.strip("/").split("/")
        parent = self.root_folder
        for part in parts:
            parent = self.find_folder(part, parent)
            if not parent:
                return []

        query = f"'{parent}' in parents and trashed=false"
        if mime_filter:
            query += f" and ({mime_filter})"

        try:
            results = (
                self.service.files()
                .list(
                    q=query,
                    fields="files(id, name, mimeType, createdTime, size)",
                    orderBy="createdTime desc",
                    pageSize=100,
                )
                .execute()
            )
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
            return []

    def list_images(self, folder_path):
        return self.list_files(
            folder_path, mime_filter="mimeType='image/png' or mimeType='image/jpeg'"
        )

    def list_csvs(self, folder_path):
        return self.list_files(
            folder_path,
            mime_filter="mimeType='text/csv' or name contains '.csv'",
        )

    def download_file(self, file_id, destination):
        try:
            request = self.service.files().get_media(fileId=file_id)
            with io.FileIO(destination, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            logger.info(f"Descargado: {destination}")
            return True
        except Exception as e:
            logger.error(f"Error descargando {file_id}: {e}")
            return False

    def upload_file(self, file_path, folder_path):
        name = Path(file_path).name
        parts = folder_path.strip("/").split("/")
        parent = self.root_folder
        for part in parts:
            parent = self.get_or_create_folder(part, parent)

        metadata = {"name": name, "parents": [parent]}
        try:
            media = MediaFileUpload(file_path, resumable=True)
            f = (
                self.service.files()
                .create(body=metadata, media_body=media, fields="id,webViewLink")
                .execute()
            )
            logger.info(f"Subido: {name} -> {folder_path}")
            return f.get("id")
        except Exception as e:
            logger.error(f"Error subiendo {name}: {e}")
            return None

    def get_upload_link(self, folder_path):
        """Genera un link para que cualquiera pueda subir archivos"""
        parts = folder_path.strip("/").split("/")
        parent = self.root_folder
        for part in parts:
            parent = self.get_or_create_folder(part, parent)

        # Dar permiso de escritura a cualquiera con el link
        try:
            self.service.permissions().create(
                fileId=parent,
                body={"type": "anyone", "role": "writer"},
                fields="id",
            ).execute()
            f = self.service.files().get(fileId=parent, fields="webViewLink").execute()
            return f.get("webViewLink")
        except Exception as e:
            logger.error(f"Error generando link de subida: {e}")
            return None

    def delete_file(self, file_id):
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error eliminando {file_id}: {e}")
            return False
