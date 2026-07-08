import re
import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

from .config import Config

logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
        self.patterns = {
            "fecha": r"(\d{2}[/\-.]\d{2}[/\-.]\d{4})",
            "fecha_alt": r"(\d{2}[/\-.]\d{2}[/\-.]\d{2})",
            "comprobante": r"(?:COMPROBANTE|N[°º]|NUMERO|#)\s*:?\s*(\d{6,12})",
            "valor_ref": r"VALOR\s*:?\s*\$?([\d.,]+)",
            "valor_num": r"\$\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?)",
            "cuenta": r"(\d{4})\s*(?:-\s*\d{4})?\s*(?:\b|$)",
        }

    def preprocess(self, image_path):
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"No se pudo leer la imagen: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        h, w = thresh.shape
        if w < 1000:
            scale = 1000 / w
            thresh = cv2.resize(thresh, (int(w * scale), int(h * scale)))
        return thresh

    def extract_text(self, image_path):
        try:
            processed = self.preprocess(image_path)
            cfg = f"--oem 3 --psm 6 -l {Config.OCR_LANGUAGE}"
            text1 = pytesseract.image_to_string(processed, config=cfg)

            img = Image.open(image_path)
            text2 = pytesseract.image_to_string(img, config=cfg)

            # Usar el texto con más contenido
            text = text1 if len(text1) > len(text2) else text2
            logger.info(f"Texto extraído ({len(text)} chars):\n{text[:300]}")
            return text
        except Exception as e:
            logger.error(f"Error OCR: {e}")
            return ""

    def extract_data(self, text):
        data = {"fecha": None, "comprobante": None, "valor": None, "cuenta": None}

        # ── Fecha ──
        m = re.search(self.patterns["fecha"], text)
        if m:
            data["fecha"] = m.group(1)
        else:
            m = re.search(self.patterns["fecha_alt"], text)
            if m:
                parts = re.split(r"[/\-.]", m.group(1))
                if len(parts) == 3 and len(parts[2]) == 2:
                    y = 2000 + int(parts[2]) if int(parts[2]) < 30 else 1900 + int(parts[2])
                    data["fecha"] = f"{parts[0]}/{parts[1]}/{y}"

        # ── Comprobante ──
        m = re.search(self.patterns["comprobante"], text, re.IGNORECASE)
        if m:
            data["comprobante"] = m.group(1).strip()
        else:
            # Buscar cualquier número de 6-12 dígitos aislado
            nums = re.findall(r"\b(\d{6,12})\b", text)
            if nums:
                data["comprobante"] = max(nums, key=len)

        # ── Valor ──
        m = re.search(self.patterns["valor_ref"], text, re.IGNORECASE)
        if m:
            data["valor"] = self._parse_monto(m.group(1))
        if not data["valor"]:
            m = re.search(self.patterns["valor_num"], text)
            if m:
                data["valor"] = self._parse_monto(m.group(1))
        if not data["valor"]:
            # Buscar números grandes que parezcan montos
            montos = re.findall(r"\$?\s*(\d{1,3}(?:[\.,]\d{3})+(?:[\.,]\d{2})?)", text)
            for mt in montos:
                v = self._parse_monto(mt)
                if v and v > 1000:
                    data["valor"] = v
                    break

        # ── Cuenta destino ──
        for cid in Config.CUENTAS:
            if cid in text:
                data["cuenta"] = cid
                break
        if not data["cuenta"]:
            m = re.search(self.patterns["cuenta"], text)
            if m and m.group(1) in Config.CUENTAS:
                data["cuenta"] = m.group(1)

        # ── Producto destino ──
        data["producto"] = Config.CUENTAS.get(data["cuenta"], f"Desconocida ({data['cuenta']})")

        return data

    def _parse_monto(self, s):
        s = s.strip().replace(" ", "")
        # Detectar formato: 1.234.567,89 o 1,234,567.89
        if s.count(",") > 1 and s.count(".") <= 1:
            # Formato colombiano: 1.234.567,89
            s = s.replace(".", "").replace(",", ".")
        elif s.count(".") > 1 and s.count(",") <= 1:
            # Formato inglés: 1,234,567.89
            s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    def process_image(self, image_path):
        try:
            text = self.extract_text(image_path)
            if not text:
                return None
            data = self.extract_data(text)
            if not data.get("comprobante") and not data.get("valor"):
                return None
            data["archivo"] = Path(image_path).name
            data["fecha_procesamiento"] = datetime.now().isoformat()
            return data
        except Exception as e:
            logger.error(f"Error procesando {image_path}: {e}")
            return None
