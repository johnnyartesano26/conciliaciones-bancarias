# 🤖 Agente de Conciliación Bancaria

Sistema automatizado de conciliación de comprobantes de pago contra extractos bancarios usando OCR (Tesseract) + Google Drive + GitHub Actions.

## 🎯 ¿Qué hace?

1. **Lee** imágenes de comprobantes de pago desde Google Drive
2. **Extrae** con OCR: fecha, número de comprobante, valor y cuenta destino
3. **Clasifica** automáticamente según 4 cuentas destino
4. **Concilia** contra el extracto bancario (CSV)
5. **Genera** un dashboard con checklist: ✅ CONFIRMADO / ❌ NO CONFIRMADO

## 📋 Cuentas configuradas

| Últimos 4 dígitos | Destino |
|---|---|
| 3598 | Cervecería Madre Monte (3598) |
| 1490 | Juliana Cardona (1490) |
| 9437 | Johnny Guerrero (9437) |
| 2216 | Cervecería Madre Monte (2216) |

## 🚀 Cómo usar

### 1. Configurar Google Drive

1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com)
2. Habilita la API de Google Drive
3. Crea una cuenta de servicio y descarga el JSON de credenciales
4. Convierte el JSON a base64: `base64 -w0 credenciales.json`
5. Agrégala como secreto en GitHub: `GOOGLE_DRIVE_CREDENTIALS`

### 2. Configurar GitHub Secrets

| Secreto | Descripción |
|---|---|
| `GOOGLE_DRIVE_CREDENTIALS` | JSON de credenciales en base64 |
| `DRIVE_FOLDER_ID` | ID de la carpeta raíz en Google Drive |
| `DRIVE_UPLOAD_LINK` | Link público para subir comprobantes |
| `DRIVE_LINK_EXTRACTOS` | Link público para subir extractos |

### 3. Subir archivos

- **Comprobantes:** Sube fotos PNG/JPG a la carpeta `Comprobantes/Pendientes` en Drive
- **Extracto bancario:** Sube un archivo CSV a la carpeta `Extractos_Bancarios`

### 4. Ejecutar

El workflow de GitHub Actions se ejecuta cada 6 horas automáticamente, o puedes ejecutarlo manualmente desde la pestaña Actions del repositorio.

## 📊 Dashboard

El dashboard se publica automáticamente en GitHub Pages:
**https://johnnyartesano26.github.io/conciliaciones-bancarias/**

## 🏗️ Estructura del proyecto

```
conciliaciones-bancarias/
├── src/
│   ├── config.py              # Configuración y cuentas
│   ├── drive_manager.py       # Gestión de Google Drive
│   ├── ocr_processor.py       # OCR con Tesseract
│   ├── conciliador.py         # Lógica de conciliación
│   ├── dashboard_generator.py # Generador del dashboard
│   └── main.py                # Orquestador principal
├── data/
│   ├── checklist.json         # Datos de conciliación (JSON)
│   └── output/                # CSVs generados
├── index.html                 # Dashboard (GitHub Pages)
├── .github/workflows/         # GitHub Actions
└── requirements.txt
```

## 🛠️ Stack

- **Python 3.11+** con pandas, OpenCV, pytesseract
- **Google Drive API** para almacenamiento
- **GitHub Actions** para procesamiento automático
- **GitHub Pages** para el dashboard
- **Tesseract OCR** (español) para lectura de comprobantes
