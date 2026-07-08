import json
import logging
from datetime import datetime
from .config import Config

logger = logging.getLogger(__name__)


class DashboardGenerator:
    def generate(self, resultados, resumen, drive=None):
        """Genera solo el archivo checklist.json. El HTML es estático (carga el JSON dinámicamente)."""

        checklist_data = {
            "titulo": "Conciliación de Comprobantes",
            "subtitulo": "Comprobantes vs Extracto Bancario",
            "actualizado": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "resumen": resumen,
            "comprobantes": resultados,
            "cuentas": [
                {"id": "3598", "nombre": "Cervecería Madre Monte (3598)"},
                {"id": "1490", "nombre": "Juliana Cardona (1490)"},
                {"id": "9437", "nombre": "Johnny Guerrero (9437)"},
                {"id": "2216", "nombre": "Cervecería Madre Monte (2216)"},
            ],
            "links_upload": {
                "pendientes": Config.DRIVE_UPLOAD_LINK or "#",
                "extractos": Config.DRIVE_LINK_EXTRACTOS or "#",
            },
        }

        # Guardar JSON (el HTML index.html lo carga dinámicamente)
        with open(Config.CHECKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(checklist_data, f, ensure_ascii=False, indent=2)

        if drive:
            drive.upload_file(str(Config.CHECKLIST_FILE), "Comprobantes/Procesados")

        logger.info(f"Checklist generado: {Config.CHECKLIST_FILE}")
