from datetime import datetime
from pathlib import Path

_LOGS_DIR = Path(__file__).parent.parent / "logs"


def write_log(
    partida_path: Path,
    page_invoice_map: dict[int, Path | None],
    output_pdf: Path | None,
) -> Path:
    """
    Genera logs/YYYY-MM-DD_HH-MM-SS.txt con:
        - Fecha y hora
        - Archivo de partida procesado
        - Por cada página: número, factura encontrada o faltante
        - PDF final generado (o error)
    """
    _LOGS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = _LOGS_DIR / f"{timestamp}.txt"

    total = len(page_invoice_map)
    found = sum(1 for v in page_invoice_map.values() if v is not None)
    missing = total - found

    lines = [
        f"FECHA           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"ARCHIVO PARTIDA : {partida_path}",
        "",
        "── RESUMEN ──────────────────────────────────",
        f"  Páginas de partida : {total}",
        f"  Con factura        : {found}",
        f"  Sin factura        : {missing}",
        "",
        "── DETALLE POR PÁGINA ───────────────────────",
    ]

    for page_idx in sorted(page_invoice_map):
        invoice = page_invoice_map[page_idx]
        status = f"  ✔ {invoice.name}" if invoice else "  ✘ sin factura encontrada"
        lines.append(f"  Página {page_idx + 1:>3}  →  {status}")

    lines += [
        "",
        "── PDF FINAL ────────────────────────────────",
        f"  {output_pdf}" if output_pdf else "  No se generó (ocurrió un error).",
    ]

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path
