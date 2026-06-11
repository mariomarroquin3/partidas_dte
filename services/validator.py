def validate_results(search_result: dict) -> dict:
    """
    Analiza el resultado de finder.search_pdfs y produce un resumen
    con duplicados, faltantes e inconsistencias.

    Parámetro:
        search_result: dict devuelto por finder.search_pdfs

    Devuelve:
        {
            "total_targets":    int,
            "total_found":      int,
            "total_missing":    int,
            "total_duplicates": int,
            "missing":          [code, ...],
            "duplicates":       {code: [Path, ...], ...},
            "ok":               bool,   # True si no hay faltantes ni duplicados
        }
    """
    found = search_result["found"]
    missing = search_result["missing"]
    duplicates = search_result["duplicates"]

    total_targets = len(found)
    total_found = sum(1 for paths in found.values() if paths)
    total_missing = len(missing)
    total_duplicates = len(duplicates)

    return {
        "total_targets": total_targets,
        "total_found": total_found,
        "total_missing": total_missing,
        "total_duplicates": total_duplicates,
        "missing": missing,
        "duplicates": duplicates,
        "ok": total_missing == 0 and total_duplicates == 0,
    }
