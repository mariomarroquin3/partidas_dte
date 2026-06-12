# 📊 Flujo de la Aplicación - Partidas DTE

## 🎯 Propósito General

La aplicación **Partidas DTE** automatiza el proceso de relacionar partidas contables (documentos PDF) con sus facturas correspondientes. El flujo integra archivos PDF, extrae identificadores únicos (códigos de generación y números de control), busca las facturas relacionadas y genera un PDF unificado e intercalado.

---

## 🔄 Flujo Paso a Paso

### **PASO 1: Seleccionar PDF de Partida**
**Archivo:** `ui/main_window.py` → `_select_partida()`

```
┌─────────────────────────────────────┐
│ Usuario: Click "📂 Seleccionar partida"
└────────────┬────────────────────────┘
             │
             ▼
    Abre diálogo de archivo
    (filedialog.askopenfilename)
             │
             ▼
    Valida: ¿Es un .pdf?
             │
             ├─ SÍ → Guarda en self._partida_path
             │       Actualiza etiqueta con ruta
             │       Llama a _extract_per_page()
             │
             └─ NO → Cancela
```

**Entrada:** Ruta del archivo PDF de partida  
**Salida:** `self._partida_path` guardado en memoria  
**Siguiente paso:** Extracción de identificadores

---

### **PASO 2: Extraer Identificadores por Página**
**Archivos:** 
- `services/pdf_reader.py` → `extract_pages_text()`
- `services/extractor.py` → `extract_identifiers()`

```
┌──────────────────────────────────────────────┐
│ _extract_per_page()
└────────┬─────────────────────────────────────┘
         │
         ▼
1️⃣ extract_pages_text(partida_path)
   ├─ Abre PDF con pdfplumber
   ├─ Extrae texto de CADA página
   └─ Devuelve lista: [texto_pág1, texto_pág2, ...]
         │
         ▼
2️⃣ Para CADA página:
   extract_identifiers(texto_página)
         │
         ├─ normalize_pdf_text(texto)
         │  ├─ Convierte a mayúsculas
         │  ├─ Normaliza saltos de línea (\r, \t)
         │  └─ Repara UUIDs rotos/parciales
         │
         ├─ Busca patrones:
         │  ├─ UUIDs: [A-F0-9]{8}-[A-F0-9]{4}-...
         │  └─ Controles: DTE-\d{2}-[A-Z0-9\-]+
         │
         └─ Devuelve: {
                "generation_codes": [...],
                "control_numbers": [...]
            }
         │
         ▼
3️⃣ Almacena resultados
   self._page_identifiers = [
       {"generation_codes": [...], "control_numbers": [...]},
       {"generation_codes": [...], "control_numbers": [...]},
       ...
   ]
         │
         ▼
4️⃣ Actualiza UI:
   ├─ Muestra contador: "Total: N identificadores"
   ├─ Lista cada página con sus códigos
   └─ Activa botón "Paso 3"
```

**Entrada:** PDF de partida con texto  
**Proceso Crítico:** 
- **Normalización:** Repara UUIDs que aparecen en múltiples líneas o con basura entre caracteres
- **Extracción:** Usa regex avanzado con lookahead/lookbehind para evitar falsas coincidencias

**Salida:** 
```
self._page_identifiers: list[dict]
  Página 1 → [UUID-001, DTE-12-ABC123]
  Página 2 → [UUID-002]
  Página 3 → [] (sin identificador)
```

**Punto de Optimización:** 
- ⚠️ La reparación de UUIDs es intensiva en regex (ver extractor.py líneas 30-80)
- El procesamiento se hace **secuencial por página** (podría paralelizarse)

---

### **PASO 3: Seleccionar Carpeta de Facturas**
**Archivo:** `ui/main_window.py` → `_select_folder()`

```
┌────────────────────────────────────┐
│ Usuario: Click "📁 Seleccionar carpeta"
└────────┬─────────────────────────────┘
         │
         ▼
    Abre diálogo de carpeta
         │
         ▼
    Valida: ¿Existe la carpeta?
         │
         ├─ SÍ → Guarda en self._search_folder
         │       Actualiza etiqueta
         │       Activa botón "Buscar facturas"
         │
         └─ NO → Cancela
```

**Entrada:** Ruta a carpeta con PDFs de facturas  
**Salida:** `self._search_folder` en memoria  
**Nota:** La carpeta puede contener subcarpetas (búsqueda recursiva en paso siguiente)

---

### **PASO 4: Buscar Facturas (con índice de facturas)**
**Archivo:** `services/finder.py` → `search_pdfs()`

```
┌──────────────────────────────────────────────────────┐
│ Usuario: Click "🔍 Buscar facturas"
│ (requiere Paso 1 Y Paso 3 completados)
└────────┬──────────────────────────────────────────────┘
         │
         ▼
1️⃣ Construir (o reusar) índice de facturas
   - La primera vez que se llama en una carpeta, se recorre UNA vez.
   - Se abre cada PDF una sola vez con pdfplumber.
   - Se extrae solo la primera página: pdf.pages[0].extract_text()[:3000]
   - Se obtienen códigos UUID y DTE desde esa página.
   - El índice queda como:
       {
         "UUID-001": [Path/factura_A.pdf],
         "DTE-12-ABC123": [Path/factura_B.pdf],
         ...
       }
         │
         ▼
2️⃣ Generar búsqueda rápida
   - Para cada código objetivo, el índice devuelve la lista de PDFs asociados.
   - No se reabre cada PDF por cada partida.
         │
         ▼
3️⃣ Construir mapeo de resultados
   found = {
       "UUID-001": [Path/factura_A.pdf, Path/factura_C.pdf],
       "DTE-12-ABC123": [Path/factura_B.pdf],
       "UUID-002": [],
       ...
   }

   missing = [UUID-002, ...]
   duplicates = {
       "UUID-001": [factura_A.pdf, factura_C.pdf]
   }
         │
         ▼
4️⃣ Validar resultados
   validator.validate_results(search_result)
   ├─ total_targets: 20
   ├─ total_found: 18
   ├─ total_missing: 2
   ├─ total_duplicates: 1
   └─ ok: False (hay faltantes)
         │
         ▼
5️⃣ Actualizar mapeo página → factura
   self._page_invoice_map = {
       0: Path/factura_A.pdf,
       1: None,
       2: Path/factura_B.pdf,
       ...
   }
         │
         ▼
6️⃣ Mostrar resultados en UI
   ├─ Resumen: "Encontradas: 18/20"
   ├─ Lista códigos encontrados con ruta
   ├─ Alerta sobre faltantes/duplicados
   └─ Activa botón "Generar PDF"
```

**Entrada:** 
- `target_codes` (códigos de partida)
- `folder` (carpeta de facturas)

**Proceso Crítico:**
- ✅ La carpeta se procesa una sola vez para construir el índice
- ✅ Solo se lee la primera página de cada factura
- ✅ Texto limitado a los primeros 3000 caracteres
- ✅ Cada PDF se abre una sola vez durante la indexación
- ⚠️ El índice se reusa en llamadas sucesivas para la misma carpeta

**Salida:** 
```python
search_result = {
    "found": {código: [Path, ...], ...},
    "missing": [código, ...],
    "duplicates": {código: [Path, ...], ...}
}

page_invoice_map = {
    0: Path | None,
    1: Path | None,
    ...
}
```

**Métricas de indexación:**
- Facturas encontradas: X
- Facturas indexadas: Y
- Identificadores únicos: Z
- Tiempo de indexación: N segundos

---

### **PASO 5 & 6: Generar PDF Unificado**
**Archivo:** `services/merger.py` → `merge_interleaved()`

```
┌──────────────────────────────────────────────────────┐
│ Usuario: Click "💾 Generar PDF"
│ (requiere Paso 4 completado)
└────────┬──────────────────────────────────────────────┘
         │
         ▼
1️⃣ Usuario elige ubicación destino
   filedialog.asksaveasfilename()
   ├─ Define nombre del archivo
   └─ Define carpeta de salida
         │
         ▼
2️⃣ merge_interleaved(
       partida_path,
       page_invoice_map,
       output_path
   )
         │
         ▼
3️⃣ Crear PdfWriter
   writer = PdfWriter()
         │
         ▼
4️⃣ Abrir PDF de partida
   partida_reader = PdfReader(partida_path)
         │
         ▼
5️⃣ Para CADA página de partida:
   
   ┌─ Página 1 (partida) ──┐
   │                        │
   ├─ Páginas factura 1     │
   │ (si existe)            │
   │                        │
   ├─ Página 2 (partida) ───┤
   │                        │
   ├─ Páginas factura 2     │  ← PDF FINAL
   │ (si existe)            │
   │                        │
   ├─ Página 3 (partida) ───┤
   │                        │
   └─ Sin factura           ┘
   
   for page_idx, partida_page in enumerate(partida_reader.pages):
       writer.add_page(partida_page)
       
       invoice_path = page_invoice_map.get(page_idx)
       if invoice_path is not None:
           if invoice_path not in invoice_readers:
               invoice_readers[invoice_path] = PdfReader(invoice_path)
           
           for inv_page in invoice_readers[invoice_path].pages:
               writer.add_page(inv_page)
         │
         ▼
6️⃣ Guardar PDF final
   writer.write(output_path)
         │
         ▼
7️⃣ Actualizar estado
   ✅ "PDF generado exitosamente"
```

**Entrada:** 
- `partida_path`: PDF de partida
- `page_invoice_map`: Mapeo {índice_página: Path_factura}
- `output_path`: Ubicación destino

**Proceso:**
- **Caché de lectores:** Evita abrir el mismo PDF múltiples veces
- **Orden intercalado:** Maximiza legibilidad (partida → factura → partida → ...)

**Salida:** 
```
Archivo PDF unificado en output_path
con estructura:
  [Pág 1 Partida]
  [Pág 1-N Factura 1]
  [Pág 2 Partida]
  [Pág 1-M Factura 2]
  ...
```

---

### **PASO 7: Estado Final**
**Archivo:** `ui/main_window.py` → `_set_status()`

```
┌────────────────────────────┐
│ Mostrar mensaje final
├─ ✅ Éxito (verde)
├─ ⚠️  Advertencia (amarillo)
└─ ❌ Error (rojo)
```

---

## 🏗️ Arquitectura de Servicios

```
┌─────────────────────────────────────────────────────┐
│                   MainWindow (UI)                    │
│                  (ui/main_window.py)                 │
└────┬────────┬────────────┬────────────┬──────────────┘
     │        │            │            │
     ▼        ▼            ▼            ▼
  ┌──────┐ ┌───────────┐ ┌────────┐ ┌──────────┐
  │pdf_  │ │ extractor │ │ finder │ │ merger   │
  │reader│ │           │ │        │ │          │
  └──────┘ └───────────┘ └────────┘ └──────────┘
     │        │            │            │
     └────────┴────────────┴────────────┘
              │
              ▼
     ┌──────────────────┐
     │   validator      │
     │  (opcional)      │
     └──────────────────┘
              │
              ▼
     ┌──────────────────┐
     │   logger         │
     │ (logging events) │
     └──────────────────┘
```

### Detalle de Servicios:

| Servicio | Función Principal | Entrada | Salida |
|----------|------------------|---------|--------|
| **pdf_reader** | Extraer texto de PDFs | `Path` a PDF | `list[str]` (texto por página) |
| **extractor** | Extraer UUIDs y códigos DTE | `str` (texto) | `dict` con códigos encontrados |
| **finder** | Buscar facturas en carpeta | `Path` folder, `list` códigos | `dict` con mapeo encontrado/faltante |
| **merger** | Generar PDF intercalado | `Path` partida, `dict` mapeo | `Path` PDF final |
| **validator** | Validar resultados búsqueda | `dict` resultado | `dict` validación |
| **logger** | Registrar eventos | eventos | Archivos log |

---

## ⚙️ Puntos de Optimización Identificados

### 🔴 **Críticos (Alto Impacto)**

1. **Búsqueda recursiva sin índices**
   - **Problema:** `folder.rglob("*.pdf")` abre TODOS los PDFs
   - **Impacto:** O(n) donde n = cantidad de PDFs en carpeta
   - **Solución:** 
     - Indexar PDFs al cargar carpeta
     - Usar búsqueda paralela (multiprocessing)
     - Cache de índices (hash de contenido)

2. **Normalización de UUID con regex recursivo**
   - **Problema:** Patrón híbrido en extractor.py líneas 30-80
   - **Impacto:** O(m²) donde m = longitud de texto
   - **Solución:**
     - Compilar regex una sola vez (cache)
     - Limitar búsqueda a bloques de 500 caracteres
     - Usar máquinas de estados en lugar de regex

3. **Lectura completa de cada PDF**
   - **Problema:** `extract_text_from_pdf()` procesa TODAS las páginas
   - **Impacto:** Memoria = sum(todas las páginas de todos los PDFs)
   - **Solución:**
     - Lectura stream de páginas
     - Buscar en primeras N páginas (donde suelen estar códigos)

### 🟡 **Medios (Rendimiento)**

4. **Extracción secuencial de páginas**
   - **Problema:** `for page in pages: extract_identifiers(page)`
   - **Solución:** Usar `ThreadPoolExecutor` con 4-8 workers

5. **UI bloqueante**
   - **Problema:** Búsqueda/merge se hacen en hilo principal
   - **Solución:** Ya usa `threading.Thread()` pero sin barra de progreso

6. **Sin caché entre pasos**
   - **Problema:** Si usuario repite búsqueda, se reprocesa todo
   - **Solución:** Guardar en caché resultados paso 2 y 4

### 🟢 **Menores (Mantenibilidad)**

7. Logging incompleto (línea `from services import logger` sin usar)
8. Sin validación de entrada en servicios
9. Rutas hardcodeadas en pruebas

---

## 📊 Flujo de Datos Completo

```
[PARTIDA.pdf]
     │
     ├─→ [pdf_reader] ──→ [Texto por página]
     │                          │
     │                          ├─→ [extractor] 
     │                          │   (normalize + regex)
     │                          │
     │                          ▼
     │              [Códigos por página]
     │                          │
     ├──────────────────────────┤
     │                          │
     │                [self._page_identifiers]
     │                          │
     └──────────────┬───────────┘
                    │
              [CARPETA_FACTURAS]
                    │
                    ├─→ [folder.rglob("*.pdf")]
                    │   (encontrar todos)
                    │
                    ├─→ [_pdf_contains_code]
                    │   (buscar en cada uno)
                    │
                    │   ├─ [pdf_reader]
                    │   ├─ [extractor]
                    │   └─ [Comparación exacta]
                    │
                    ├─→ [finder] ──→ [Resultado búsqueda]
                    │                 {found, missing, duplicates}
                    │
                    ├─→ [validator] ──→ [Validación]
                    │
                    ▼
            [self._page_invoice_map]
                    │
                    ├─→ [PARTIDA.pdf]
                    │   + [page_invoice_map]
                    │
                    ├─→ [merger]
                    │   (intercalar páginas)
                    │
                    ▼
            [SALIDA_UNIFICADO.pdf]
```

---

## 🎯 Recomendaciones de Optimización (Prioridad)

1. **🥇 Paralelizar búsqueda de PDFs**
   - Usar `concurrent.futures.ThreadPoolExecutor`
   - Procesar 4-8 PDFs simultáneamente

2. **🥈 Caché de regex compilado**
   - Mover compilación fuera de función `normalize_pdf_text()`

3. **🥉 Búsqueda limitada**
   - En `_pdf_contains_code()`: primeras 10 páginas instead de todas

4. **🏅 UI responsiva**
   - Agregar barra de progreso en hilo de búsqueda
   - Actualizar cada 0.5s

5. **🏅 Logging completo**
   - Registrar tiempo de cada paso
   - Identificar cuellos de botella

---

## 📝 Resumen Ejecutivo

| Paso | Acción | Tiempo Típico | Cuello de Botella |
|------|--------|---------------|-----------------|
| 1 | Seleccionar partida | <1s | UI |
| 2 | Extraer códigos | <2s | Regex (normalize) |
| 3 | Seleccionar carpeta | <1s | UI |
| 4 | Buscar facturas | **5-30s** | rglob + PDF lectura |
| 5-6 | Generar PDF | 1-5s | Tamaño PDF |
| **Total** | **Proceso completo** | **~10-40s** | **Paso 4** |

**El 80% del tiempo se dedica al PASO 4 (búsqueda de facturas)**
