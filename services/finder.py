from pathlib import Path

from services.pdf_reader import extract_text_from_pdf
from services.extractor import extract_identifiers


def _pdf_contains_code(pdf_path: Path, target_codes: set) -> tuple[bool, list]:
    """
    Abre un PDF, extrae sus identificadores y compara EXACTAMENTE
    contra target_codes.

    Devuelve (coincidió, lista_de_códigos_encontrados).
    """
    try:
        text = extract_text_from_pdf(pdf_path)
        found = extract_identifiers(text)
        all_codes = set(found["generation_codes"]) | set(found["control_numbers"])
        matched = [code for code in target_codes if code in all_codes]
        return bool(matched), matched
    except Exception:
        return False, []


def search_pdfs(folder: Path, target_codes: list) -> dict:
    """
    Recorre *folder* recursivamente buscando PDFs que contengan
    alguno de los códigos en *target_codes*.

    Comparación EXACTA: found_code == target_code.

    Devuelve:
        {
            "found":      {code: [Path, ...], ...},   # código → archivos que lo contienen
            "missing":    [code, ...],                # códigos sin ningún PDF
            "duplicates": {code: [Path, ...], ...},   # código en más de un PDF
        }
    """
    targets = set(target_codes)
    found: dict[str, list[Path]] = {code: [] for code in targets}

    all_pdfs = list(folder.rglob("*.pdf"))

    for pdf_path in all_pdfs:
        matched, codes = _pdf_contains_code(pdf_path, targets)
        if matched:
            for code in codes:
                found[code].append(pdf_path)

    missing = [code for code, paths in found.items() if not paths]
    duplicates = {code: paths for code, paths in found.items() if len(paths) > 1}

    return {
        "found": found,
        "missing": missing,
        "duplicates": duplicates,
    }
