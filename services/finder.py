from pathlib import Path
import time
from typing import Dict

import pdfplumber

from services.extractor import extract_identifiers
from services import logger

# Caché simple por carpeta para evitar re-indexar en llamadas repetidas
_INDEX_CACHE: dict = {
    "folder": None,  # Path
    "index": None,   # dict: code -> [Path, ...]
    "metrics": None, # dict de métricas
}


def _build_invoice_index(folder: Path, max_chars: int = 3000) -> dict:
    """
    Recorre la carpeta `folder` UNA vez y construye un índice en memoria
    que mapea identificador -> lista de rutas de PDFs que lo contienen.

    Optimizaciones implementadas:
    - Abre cada PDF una sola vez (con pdfplumber)
    - Lee únicamente la primera página
    - Analiza sólo los primeros `max_chars` caracteres
    """
    start = time.perf_counter()
    all_pdfs = list(folder.rglob("*.pdf"))
    total_pdfs = len(all_pdfs)

    index: Dict[str, list[Path]] = {}
    processed_pdfs = 0

    for pdf_path in all_pdfs:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    continue
                # Leer sólo la primera página y limitar a max_chars
                text = pdf.pages[0].extract_text() or ""
                text = text[:max_chars]

                found = extract_identifiers(text)
                codes = set(found.get("generation_codes", [])) | set(found.get("control_numbers", []))
                if not codes:
                    continue

                processed_pdfs += 1
                for code in codes:
                    index.setdefault(code, []).append(pdf_path)
        except Exception:
            # Ignorar PDFs problemáticos y continuar
            continue

    elapsed = time.perf_counter() - start

    metrics = {
        "total_pdfs": total_pdfs,
        "processed_pdfs": processed_pdfs,
        "unique_identifiers": len(index),
        "elapsed_seconds": elapsed,
    }

    # Guardar métricas en logs y caché
    logger.write_index_log(folder, metrics)

    return {"index": index, "metrics": metrics}


def search_pdfs(folder: Path, target_codes: list) -> dict:
    """
    Busca rápidamente PDFs que contengan alguno de los códigos en *target_codes*.

    Implementación optimizada:
    - Construye un índice (una sola pasada) por carpeta la primera vez
    - Reusa el índice en llamadas posteriores para la misma carpeta

    Devuelve la misma estructura que antes:
        {
            "found":      {code: [Path, ...], ...},
            "missing":    [code, ...],
            "duplicates": {code: [Path, ...], ...},
        }
    """
    # Reusar índice si ya fue construido para esta carpeta
    folder_resolved = folder.resolve()
    if _INDEX_CACHE["folder"] != folder_resolved or _INDEX_CACHE["index"] is None:
        built = _build_invoice_index(folder_resolved)
        _INDEX_CACHE["folder"] = folder_resolved
        _INDEX_CACHE["index"] = built["index"]
        _INDEX_CACHE["metrics"] = built["metrics"]

    index = _INDEX_CACHE["index"]

    targets = set(target_codes)
    found: dict[str, list[Path]] = {code: list(index.get(code, [])) for code in targets}

    missing = [code for code, paths in found.items() if not paths]
    duplicates = {code: paths for code, paths in found.items() if len(paths) > 1}

    return {
        "found": found,
        "missing": missing,
        "duplicates": duplicates,
    }
