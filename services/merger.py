from pathlib import Path
from pypdf import PdfWriter, PdfReader


def merge_interleaved(
    partida_path: Path,
    page_invoice_map: dict[int, Path | None],
    output_path: Path,
) -> Path:
    """
    Genera un PDF con la siguiente estructura por cada página de la partida:

        [Página de partida N]
        [Páginas de la factura relacionada]  ← solo si se encontró
        [Página de partida N+1]
        [Páginas de la factura relacionada]
        ...

    Parámetros:
        partida_path     : PDF de la partida contable.
        page_invoice_map : {índice_página: Path | None}
                           None cuando no se encontró factura para esa página.
        output_path      : Ruta donde se guarda el PDF final.

    Devuelve la ruta del PDF generado.
    """
    writer = PdfWriter()
    partida_reader = PdfReader(str(partida_path))

    # Caché para no abrir el mismo PDF de factura varias veces
    invoice_readers: dict[Path, PdfReader] = {}

    for page_idx, partida_page in enumerate(partida_reader.pages):
        # 1. Agregar la página de la partida
        writer.add_page(partida_page)

        # 2. Agregar inmediatamente las páginas de la factura (si existe)
        invoice_path = page_invoice_map.get(page_idx)
        if invoice_path is not None:
            resolved = invoice_path.resolve()
            if resolved not in invoice_readers:
                invoice_readers[resolved] = PdfReader(str(resolved))
            for inv_page in invoice_readers[resolved].pages:
                writer.add_page(inv_page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
