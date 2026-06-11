# Partidas DTE

Aplicación de escritorio para extraer identificadores (UUID / Número de Control)
de PDFs de partidas contables, localizar las facturas DTE relacionadas dentro de
una carpeta y unirlas en un único PDF.

---

## Requisitos

- Python 3.11+
- Sistema operativo: Windows / macOS / Linux

---

## Instalación

```bash
pip install -r requirements.txt
```

---

## Uso

```bash
python app.py
```

### Flujo de la aplicación

| Paso | Acción |
|------|--------|
| 1 | Seleccionar el PDF de la partida contable |
| 2 | Ver los identificadores extraídos automáticamente |
| 3 | Seleccionar la carpeta donde están las facturas PDF |
| 4 | Ejecutar la búsqueda y revisar encontrados / faltantes / duplicados |
| 5 | Elegir la ruta donde guardar el PDF unificado |
| 6 | Unir los PDFs encontrados |
| 7 | Verificar el resultado y consultar el log generado |

---

## Estructura del proyecto

```
partidas_dte/
│
├── app.py                  # Punto de entrada
├── requirements.txt
├── README.md
│
├── ui/
│   ├── __init__.py
│   └── main_window.py      # Ventana principal (CustomTkinter)
│
├── services/
│   ├── __init__.py
│   ├── pdf_reader.py       # Extracción de texto con pdfplumber
│   ├── extractor.py        # Regex para UUID y Número de Control
│   ├── finder.py           # Búsqueda recursiva en carpeta
│   ├── merger.py           # Unión de PDFs con pypdf
│   ├── validator.py        # Detección de duplicados y faltantes
│   └── logger.py           # Generación de logs automáticos
│
└── logs/                   # Logs generados automáticamente
```

---

## Notas

- Los PDFs deben ser **digitales** (no escaneados). No se usa OCR.
- Los UUIDs partidos entre líneas por el PDF son reparados automáticamente
  antes de aplicar los patrones regex.
- Los logs se guardan en `logs/YYYY-MM-DD_HH-MM-SS.txt`.
