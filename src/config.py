import os
from pathlib import Path


class Config:
    # ── Cuentas destino ──
    CUENTAS = {
        "3598": "Cervecería Madre Monte (3598)",
        "1490": "Juliana Cardona (1490)",
        "9437": "Johnny Guerrero (9437)",
        "2216": "Cervecería Madre Monte (2216)",
    }

    # ── Google Drive ──
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")
    DRIVE_UPLOAD_LINK = os.getenv("DRIVE_UPLOAD_LINK", "")
    DRIVE_LINK_EXTRACTOS = os.getenv("DRIVE_LINK_EXTRACTOS", "")

    FOLDER_PENDIENTES = "Comprobantes/Pendientes"
    FOLDER_PROCESADOS = "Comprobantes/Procesados"
    FOLDER_EXTRACTOS = "Extractos_Bancarios"

    # ── OCR ──
    OCR_LANGUAGE = "spa"
    CONFIDENCE_THRESHOLD = 60
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")

    # ── Conciliación ──
    TOLERANCIA_DIAS = 1
    TOLERANCIA_MONTO = 50

    # ── Rutas locales ──
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    IMAGES_DIR = DATA_DIR / "imagenes"
    OUTPUT_DIR = DATA_DIR / "output"
    CHECKLIST_FILE = DATA_DIR / "checklist.json"
    DASHBOARD_FILE = BASE_DIR / "index.html"

    @classmethod
    def setup_dirs(cls):
        for d in [cls.DATA_DIR, cls.IMAGES_DIR, cls.OUTPUT_DIR]:
            d.mkdir(parents=True, exist_ok=True)
