import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from services.pdf_reader import extract_pages_text
from services.extractor import extract_identifiers
from services.finder import search_pdfs
from services.merger import merge_interleaved
from services import logger

# ── Tema ──────────────────────────────────────
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

_FONT_TITLE  = ("Segoe UI", 13, "bold")
_FONT_NORMAL = ("Segoe UI", 12)
_FONT_MONO   = ("Courier New", 11)
_PAD         = {"padx": 14, "pady": 6}


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Partidas DTE")
        self.geometry("780x720")
        self.resizable(True, True)

        # Estado interno
        self._partida_path: Path | None = None
        self._search_folder: Path | None = None
        # page_identifiers[i] → {"generation_codes": [...], "control_numbers": [...]}
        self._page_identifiers: list[dict] = []
        # page_invoice_map[i] → Path | None
        self._page_invoice_map: dict[int, Path | None] = {}

        self._build_ui()

    # ── Construcción de la UI ────────────────────────────────────────────

    def _build_ui(self):
        self._scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self._scroll.pack(fill="both", expand=True)
        f = self._scroll

        # Paso 1
        self._section(f, "Paso 1 — Seleccionar PDF de partida")
        self._lbl_partida = ctk.CTkLabel(f, text="Ningún archivo seleccionado",
                                         font=_FONT_NORMAL, anchor="w")
        self._lbl_partida.pack(fill="x", **_PAD)
        ctk.CTkButton(f, text="📂  Seleccionar partida",
                      command=self._select_partida).pack(anchor="w", **_PAD)

        # Paso 2
        self._section(f, "Paso 2 — Identificadores extraídos por página")
        self._lbl_ids_count = ctk.CTkLabel(f, text="—", font=_FONT_NORMAL, anchor="w")
        self._lbl_ids_count.pack(fill="x", **_PAD)
        self._box_ids = self._textbox(f, height=130)

        # Paso 3
        self._section(f, "Paso 3 — Seleccionar carpeta de facturas")
        self._lbl_folder = ctk.CTkLabel(f, text="Ninguna carpeta seleccionada",
                                        font=_FONT_NORMAL, anchor="w")
        self._lbl_folder.pack(fill="x", **_PAD)
        ctk.CTkButton(f, text="📁  Seleccionar carpeta",
                      command=self._select_folder).pack(anchor="w", **_PAD)

        # Paso 4
        self._section(f, "Paso 4 — Resultados: partida → factura")
        self._btn_search = ctk.CTkButton(f, text="🔍  Buscar facturas",
                                         command=self._run_search, state="disabled")
        self._btn_search.pack(anchor="w", **_PAD)
        self._lbl_search_summary = ctk.CTkLabel(f, text="—", font=_FONT_NORMAL, anchor="w")
        self._lbl_search_summary.pack(fill="x", **_PAD)
        self._box_results = self._textbox(f, height=160)

        # Pasos 5 & 6
        self._section(f, "Pasos 5 & 6 — Guardar PDF unificado")
        self._btn_merge = ctk.CTkButton(f, text="💾  Seleccionar destino y generar PDF",
                                        command=self._run_merge, state="disabled")
        self._btn_merge.pack(anchor="w", **_PAD)

        # Paso 7
        self._section(f, "Paso 7 — Estado final")
        self._lbl_status = ctk.CTkLabel(f, text="Esperando acciones…",
                                        font=_FONT_NORMAL, anchor="w")
        self._lbl_status.pack(fill="x", **_PAD)

    # ── Helpers UI ───────────────────────────────────────────────────────

    def _section(self, parent, title: str):
        ctk.CTkLabel(parent, text=title, font=_FONT_TITLE, anchor="w").pack(
            fill="x", padx=14, pady=(16, 2))
        ctk.CTkFrame(parent, height=2, fg_color="gray40").pack(
            fill="x", padx=14, pady=(0, 4))

    def _textbox(self, parent, height=100) -> ctk.CTkTextbox:
        box = ctk.CTkTextbox(parent, height=height, font=_FONT_MONO,
                             wrap="none", state="disabled")
        box.pack(fill="x", **_PAD)
        return box

    def _set_textbox(self, box: ctk.CTkTextbox, text: str):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _set_status(self, msg: str, color: str = "gray70"):
        self._lbl_status.configure(text=msg, text_color=color)

    # ── Paso 1 ───────────────────────────────────────────────────────────

    def _select_partida(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PDF de partida",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        self._partida_path = Path(path)
        self._lbl_partida.configure(text=str(self._partida_path))
        self._extract_per_page()

    # ── Paso 2: extraer identificadores por página ───────────────────────

    def _extract_per_page(self):
        self._set_status("Extrayendo identificadores por página…")
        try:
            pages_text = extract_pages_text(self._partida_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el PDF:\n{e}")
            self._set_status("Error al leer la partida.", "red")
            return

        self._page_identifiers = [extract_identifiers(t) for t in pages_text]

        lines = []
        total_ids = 0
        for i, ids in enumerate(self._page_identifiers):
            codes = ids["generation_codes"] + ids["control_numbers"]
            total_ids += len(codes)
            if codes:
                lines.append(f"  Página {i + 1:>3}  →  {codes[0]}")
                for extra in codes[1:]:
                    lines.append(f"             {extra}")
            else:
                lines.append(f"  Página {i + 1:>3}  →  (sin identificador)")

        self._lbl_ids_count.configure(
            text=f"{len(pages_text)} página(s)  ·  {total_ids} identificador(es) total"
        )
        self._set_textbox(self._box_ids, "\n".join(lines) if lines else "(ninguno)")
        self._set_status("Identificadores extraídos. Seleccione una carpeta.")
        self._update_search_button()

    # ── Paso 3 ───────────────────────────────────────────────────────────

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de facturas")
        if not folder:
            return
        self._search_folder = Path(folder)
        self._lbl_folder.configure(text=str(self._search_folder))
        self._update_search_button()

    def _update_search_button(self):
        has_ids = any(
            ids["generation_codes"] or ids["control_numbers"]
            for ids in self._page_identifiers
        )
        ready = self._search_folder is not None and has_ids
        self._btn_search.configure(state="normal" if ready else "disabled")

    # ── Paso 4: búsqueda por página ──────────────────────────────────────

    def _run_search(self):
        self._btn_search.configure(state="disabled", text="Buscando…")
        self._set_status("Buscando facturas en la carpeta seleccionada…")
        threading.Thread(target=self._search_worker, daemon=True).start()

    def _search_worker(self):
        page_invoice_map: dict[int, Path | None] = {}
        try:
            for page_idx, ids in enumerate(self._page_identifiers):
                codes = ids["generation_codes"] + ids["control_numbers"]
                if not codes:
                    page_invoice_map[page_idx] = None
                    continue

                result = search_pdfs(self._search_folder, codes)

                # Tomar el primer PDF encontrado para cualquiera de los códigos
                invoice_path: Path | None = None
                for paths in result["found"].values():
                    if paths:
                        invoice_path = paths[0]
                        break

                page_invoice_map[page_idx] = invoice_path

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error en búsqueda:\n{e}"))
            self.after(0, lambda: self._set_status("Error durante la búsqueda.", "red"))
            self.after(0, lambda: self._btn_search.configure(
                state="normal", text="🔍  Buscar facturas"))
            return

        self._page_invoice_map = page_invoice_map
        self.after(0, lambda: self._show_search_results(page_invoice_map))

    def _show_search_results(self, page_invoice_map: dict[int, Path | None]):
        total   = len(page_invoice_map)
        found   = sum(1 for v in page_invoice_map.values() if v is not None)
        missing = total - found

        self._lbl_search_summary.configure(
            text=f"Páginas: {total}  |  Con factura: {found}  |  Sin factura: {missing}"
        )

        lines = []
        for page_idx in sorted(page_invoice_map):
            invoice = page_invoice_map[page_idx]
            if invoice:
                lines.append(f"  ✔ Página {page_idx + 1:>3}  →  {invoice.name}")
            else:
                ids = self._page_identifiers[page_idx]
                codes = ids["generation_codes"] + ids["control_numbers"]
                hint = codes[0] if codes else "sin identificador"
                lines.append(
                    f"  ✘ Página {page_idx + 1:>3}  →  no encontrada  ({hint})")

        self._set_textbox(self._box_results, "\n".join(lines))
        self._btn_search.configure(state="normal", text="🔍  Buscar facturas")
        self._btn_merge.configure(state="normal")
        self._set_status("Búsqueda completada. Puede generar el PDF unificado.")

    # ── Pasos 5 & 6 ──────────────────────────────────────────────────────

    def _run_merge(self):
        output_path = filedialog.asksaveasfilename(
            title="Guardar PDF unificado como…",
            defaultextension=".pdf",
            initialfile="partida_unificada.pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not output_path:
            return

        self._btn_merge.configure(state="disabled", text="Generando…")
        self._set_status("Generando PDF intercalado…")
        threading.Thread(
            target=self._merge_worker,
            args=(Path(output_path),),
            daemon=True,
        ).start()

    def _merge_worker(self, output: Path):
        try:
            result_path = merge_interleaved(
                self._partida_path, self._page_invoice_map, output
            )
            log_path = logger.write_log(
                self._partida_path, self._page_invoice_map, result_path
            )
            self.after(0, lambda: self._finish_ok(result_path, log_path))
        except Exception as e:
            logger.write_log(self._partida_path, self._page_invoice_map, None)
            self.after(0, lambda: self._finish_error(str(e)))

    # ── Paso 7 ───────────────────────────────────────────────────────────

    def _finish_ok(self, output: Path, log_path: Path):
        self._btn_merge.configure(
            state="normal", text="💾  Seleccionar destino y generar PDF")
        self._set_status(
            f"✔ PDF generado: {output.name}  |  Log: {log_path.name}", "green")
        messagebox.showinfo(
            "Éxito",
            f"PDF unificado guardado en:\n{output}\n\nLog generado en:\n{log_path}",
        )

    def _finish_error(self, error: str):
        self._btn_merge.configure(
            state="normal", text="💾  Seleccionar destino y generar PDF")
        self._set_status("✘ Error al generar el PDF.", "red")
        messagebox.showerror("Error", f"No se pudo generar el PDF:\n{error}")
