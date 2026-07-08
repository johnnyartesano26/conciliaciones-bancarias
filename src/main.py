"""
Agente de Conciliación Bancaria — Punto de entrada principal.
Flujo:
  1. Conectar con Google Drive
  2. Buscar imágenes de comprobantes pendientes
  3. Procesar con OCR
  4. Buscar extracto bancario (CSV)
  5. Conciliar comprobantes vs extracto
  6. Generar dashboard + checklist.json
  7. Subir resultados a Drive y actualizar repo
"""

import sys
import json
import logging
from datetime import datetime

import pandas as pd

from .config import Config
from .drive_manager import GoogleDriveManager
from .ocr_processor import OCRProcessor
from .conciliador import Conciliador
from .dashboard_generator import DashboardGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("conciliador")


def main():
    logger.info("🚀 Iniciando Agente de Conciliación Bancaria")

    # 1. Setup local
    Config.setup_dirs()

    # 2. Conectar con Google Drive
    drive = None
    try:
        drive = GoogleDriveManager()
        drive.setup_structure()
        logger.info("☁️ Google Drive conectado")
    except Exception as e:
        logger.warning(f"⚠️ Sin acceso a Google Drive: {e} — modo local")

    ocr = OCRProcessor()
    conciliador = Conciliador()
    dashboard = DashboardGenerator()
    fecha_str = datetime.now().strftime("%Y-%m-%d")

    # 3. Procesar imágenes
    datos_extraidos = []

    if drive:
        imagenes = drive.list_images("Comprobantes/Pendientes")
        if imagenes:
            logger.info(f"📸 {len(imagenes)} imágenes pendientes")
            for img in imagenes:
                logger.info(f"  Procesando: {img['name']}")
                local_path = Config.IMAGES_DIR / img["name"]
                if drive.download_file(img["id"], str(local_path)):
                    data = ocr.process_image(str(local_path))
                    if data:
                        datos_extraidos.append(data)
                        logger.info(f"  ✅ {data.get('comprobante', '?')} | ${data.get('valor', 0):,.0f} | {data.get('producto', '?')}")
                    else:
                        logger.warning(f"  ⚠️ No se extrajeron datos de {img['name']}")
                # Eliminar de pendientes después de procesar
                drive.delete_file(img["id"])
        else:
            logger.info("ℹ️ No hay imágenes pendientes en Drive")
    else:
        # Modo local: procesar imágenes en data/imagenes/
        if Config.IMAGES_DIR.exists():
            for img_path in sorted(Config.IMAGES_DIR.glob("*.png")):
                logger.info(f"  Procesando local: {img_path.name}")
                data = ocr.process_image(str(img_path))
                if data:
                    datos_extraidos.append(data)
                # Mover a procesados
                (Config.IMAGES_DIR / img_path.name).rename(
                    Config.IMAGES_DIR / f"procesado_{img_path.name}"
                )

    # 4. Guardar CSV intermedio
    if datos_extraidos:
        df = pd.DataFrame(datos_extraidos)
        csv_path = Config.OUTPUT_DIR / f"comprobantes_{fecha_str}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"📄 CSV guardado: {csv_path}")

    # 5. Cargar extracto bancario
    extracto_df = None
    if drive:
        extractos = drive.list_csvs("Extractos_Bancarios")
        if extractos:
            ext = extractos[0]  # El más reciente
            ext_path = Config.DATA_DIR / ext["name"]
            if drive.download_file(ext["id"], str(ext_path)):
                extracto_df = conciliador.cargar_extracto(str(ext_path))
                if extracto_df is not None:
                    logger.info(f"🏦 Extracto cargado: {len(extracto_df)} movimientos")
    else:
        # Buscar CSV local
        local_csvs = list(Config.DATA_DIR.glob("*.csv"))
        if local_csvs:
            extracto_df = conciliador.cargar_extracto(str(local_csvs[0]))

    # 6. Conciliar
    df_comprobantes = pd.DataFrame(datos_extraidos) if datos_extraidos else pd.DataFrame()
    resultados = conciliador.conciliar(df_comprobantes, extracto_df)

    # Si no hay datos extraídos, intentar cargar resultados anteriores
    if not resultados and Config.CHECKLIST_FILE.exists():
        logger.info("ℹ️ Usando datos anteriores del checklist")
        with open(Config.CHECKLIST_FILE, "r") as f:
            prev = json.load(f)
        resultados = prev.get("comprobantes", [])

    # 7. Generar resumen y dashboard
    resumen = conciliador.generar_checklist(resultados)
    dashboard.generate(resultados, resumen, drive)

    # 8. Subir a Drive si disponible
    if drive and resultados:
        # Subir CSV de resultados
        df_r = pd.DataFrame(resultados)
        ruta_r = Config.OUTPUT_DIR / f"checklist_{fecha_str}.csv"
        df_r.to_csv(ruta_r, index=False, encoding="utf-8-sig")
        drive.upload_file(str(ruta_r), "Comprobantes/Procesados")

    logger.info(f"✅ Proceso completado: {resumen['total']} comprobantes, "
                f"{resumen['confirmados']} confirmados ({resumen['porcentaje']}%)")
    return resumen


if __name__ == "__main__":
    main()
