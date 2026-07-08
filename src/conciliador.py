import logging
from datetime import datetime

import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)


class Conciliador:
    def __init__(self):
        self.tolerancia_dias = Config.TOLERANCIA_DIAS
        self.tolerancia_monto = Config.TOLERANCIA_MONTO

    def cargar_extracto(self, csv_path):
        try:
            df = pd.read_csv(str(csv_path))
            # Normalizar nombres de columnas
            rename = {}
            for col in df.columns:
                low = col.lower().strip()
                if "fecha" in low or "date" in low:
                    rename[col] = "fecha"
                elif "comprobante" in low or "referencia" in low or "numero" in low or "n°" in low:
                    rename[col] = "comprobante"
                elif "valor" in low or "monto" in low or "amount" in low or "importe" in low:
                    rename[col] = "valor"
                elif "cuenta" in low or "account" in low:
                    rename[col] = "cuenta"
            df = df.rename(columns=rename)

            if "fecha" in df.columns:
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=True)
            if "valor" in df.columns:
                df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            if "comprobante" in df.columns:
                df["comprobante"] = df["comprobante"].astype(str).str.strip()

            logger.info(f"Extracto cargado: {len(df)} registros")
            return df
        except Exception as e:
            logger.error(f"Error cargando extracto: {e}")
            return None

    def conciliar(self, comprobantes_df, extracto_df):
        if comprobantes_df is None or len(comprobantes_df) == 0:
            return []
        if extracto_df is None or len(extracto_df) == 0:
            logger.warning("Sin extracto bancario — todos los comprobantes quedan pendientes")

        resultados = []
        for _, row in comprobantes_df.iterrows():
            match = self._buscar_coincidencia(row, extracto_df)
            estado = "✅ CONFIRMADO" if match else "❌ NO CONFIRMADO"
            resultados.append(
                {
                    "fecha": str(row.get("fecha", "")),
                    "comprobante": str(row.get("comprobante", "")),
                    "valor": float(row.get("valor", 0) or 0),
                    "producto": str(row.get("producto", "")),
                    "cuenta": str(row.get("cuenta", "")),
                    "estado": estado,
                    "archivo": str(row.get("archivo", "")),
                    "coincidencia_extracto": match,
                }
            )
        return resultados

    def _buscar_coincidencia(self, comprobante, extracto_df):
        if extracto_df is None or len(extracto_df) == 0:
            return None

        num = str(comprobante.get("comprobante", "")).strip()
        valor = float(comprobante.get("valor", 0) or 0)
        fecha_str = str(comprobante.get("fecha", ""))

        try:
            fecha = pd.to_datetime(fecha_str, dayfirst=True)
        except Exception:
            fecha = None

        # 1. Buscar por número de comprobante
        if num and "comprobante" in extracto_df.columns:
            mask = extracto_df["comprobante"].astype(str).str.contains(num, na=False)
            candidates = extracto_df[mask]
            if len(candidates) > 0:
                result = self._verificar_valor_fecha(candidates, valor, fecha)
                if result is not None:
                    return result

        # 2. Buscar por valor + fecha
        if valor > 0 and "valor" in extracto_df.columns:
            mask = abs(extracto_df["valor"] - valor) <= self.tolerancia_monto
            candidates = extracto_df[mask]
            if len(candidates) > 0 and fecha:
                result = self._verificar_valor_fecha(candidates, valor, fecha, check_val=False)
                if result is not None:
                    return result
            elif len(candidates) > 0:
                return candidates.iloc[0].to_dict()

        return None

    def _verificar_valor_fecha(self, candidates, valor, fecha, check_val=True):
        if check_val and "valor" in candidates.columns:
            candidates = candidates[
                abs(candidates["valor"] - valor) <= self.tolerancia_monto
            ]
        if fecha and "fecha" in candidates.columns:
            candidates["diff_dias"] = abs(
                pd.to_datetime(candidates["fecha"], errors="coerce") - fecha
            ).dt.days
            candidates = candidates[candidates["diff_dias"] <= self.tolerancia_dias]
        if len(candidates) > 0:
            return candidates.iloc[0].to_dict()
        return None

    def generar_checklist(self, resultados):
        total = len(resultados)
        confirmados = sum(1 for r in resultados if "CONFIRMADO" in r["estado"])
        no_confirmados = total - confirmados

        por_cuenta = {}
        for r in resultados:
            p = r.get("producto", "Desconocido")
            if p not in por_cuenta:
                por_cuenta[p] = {"total": 0, "confirmados": 0}
            por_cuenta[p]["total"] += 1
            if "CONFIRMADO" in r["estado"]:
                por_cuenta[p]["confirmados"] += 1

        for p in por_cuenta:
            t = por_cuenta[p]["total"]
            c = por_cuenta[p]["confirmados"]
            por_cuenta[p]["porcentaje"] = round((c / t) * 100, 1) if t > 0 else 0

        return {
            "total": total,
            "confirmados": confirmados,
            "no_confirmados": no_confirmados,
            "porcentaje": round((confirmados / total) * 100, 1) if total > 0 else 0,
            "por_cuenta": por_cuenta,
            "fecha_ultima_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
