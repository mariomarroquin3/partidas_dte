import re

_UUID_PATTERN = re.compile(
    r'[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}',
    re.IGNORECASE
)

_CONTROL_PATTERN = re.compile(
    r'DTE-\d{2}-[A-Z0-9\-]+',
    re.IGNORECASE
)

def normalize_pdf_text(text: str) -> str:
    text = text.upper()

    # 1. Normalizar saltos básicos
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")

    # 2. Definir patrón híbrido para UUIDs (normales y rotos)
    # (?<![A-Z0-9]) y (?![A-Z0-9]) aseguran que los bloques sean exactamente de esa 
    # longitud y no formen parte de una palabra más larga.
    # JUNK captura la basura (texto, saltos, espacios) entre bloques, máximo 30 chars.
    H8  = r'(?<![A-Z0-9])([A-F0-9]{8})(?![A-Z0-9])'
    H4  = r'(?<![A-Z0-9])([A-F0-9]{4})(?![A-Z0-9])'
    H12 = r'(?<![A-Z0-9])([A-F0-9]{12})(?![A-Z0-9])'
    JUNK = r'([\s\S]{0,30}?)'
    
    repair_pattern = re.compile(
        f"{H8}{JUNK}{H4}{JUNK}{H4}{JUNK}{H4}{JUNK}{H12}",
        re.IGNORECASE
    )

    def uuid_replacer(match):
        # Extraer bloques hexadecimales y la "basura" (j1, j2, j3, j4)
        p1, j1, p2, j2, p3, j3, p4, j4, p5 = match.groups()
        
        clean_uuid = f"{p1}-{p2}-{p3}-{p4}-{p5}"
        
        # Consolidar la basura y limpiarla de guiones/espacios muertos
        junk = f"{j1} {j2} {j3} {j4}"
        junk_clean = re.sub(r'[\s\-]+', ' ', junk).strip()
        
        # Si hay texto real en medio (ej. "PARTIDA Nº 4"), lo salvamos
        # poniéndolo antes del UUID. Así no perdemos info para el resto del parsing.
        if junk_clean:
            return f"{junk_clean} {clean_uuid}"
        
        # Si era un UUID normal (o solo separado por saltos), devolvemos el UUID limpio
        return clean_uuid

    # Aplicar la reparación inteligente
    text = repair_pattern.sub(uuid_replacer, text)

    # 3. Limpiar múltiples espacios finales
    text = re.sub(r'\s+', ' ', text)

    return text


def extract_identifiers(text: str):
    clean_text = normalize_pdf_text(text)
    print("\n" + "=" * 80)
    print(repr(clean_text))
    print("=" * 80 + "\n")

    generation_codes = list({
        match.upper()
        for match in _UUID_PATTERN.findall(clean_text)
    })

    control_numbers = list({
        match.upper()
        for match in _CONTROL_PATTERN.findall(clean_text)
    })

    return {
        "generation_codes": generation_codes,
        "control_numbers": control_numbers
    }


def extract_iva_info(text: str):
    clean_text = normalize_pdf_text(text)

    # 1) Extraer todos los códigos de generación (ahora detectará los reconstruidos)
    generation_codes = list(set(
        match.upper()
        for match in _UUID_PATTERN.findall(clean_text)
    ))

    results = []

    # 2) Para cada código de generación, extraer la información asociada
    for code in generation_codes:
        code_idx = clean_text.find(code)
        if code_idx == -1:
            continue

        # Segmento de texto que está ANTES del código de generación
        prefix = clean_text[:code_idx]

        # --------------------------------------
        # PRECIO UNITARIO
        # --------------------------------------
        unit_price_match = re.search(
            r'PRECIO UNITARIO\s+([0-9,.]+)',
            prefix,
            re.IGNORECASE
        )

        unit_price = None
        if unit_price_match:
            unit_price_str = unit_price_match.group(1).replace(',', '.')
            try:
                unit_price = float(unit_price_str)
            except ValueError:
                pass

        # --------------------------------------
        # CANTIDAD
        # --------------------------------------
        cantidad_match = re.search(
            r'CANTIDAD\s+([0-9,.]+)',
            prefix,
            re.IGNORECASE
        )

        cantidad = None
        if cantidad_match:
            cantidad_str = cantidad_match.group(1).replace(',', '.')
            try:
                cantidad = float(cantidad_str)
            except ValueError:
                pass

        # --------------------------------------
        # CÁLCULO FINAL IVA
        # --------------------------------------
        iva_amount = None
        subtotal = None

        if unit_price is not None and cantidad is not None:
            subtotal = unit_price * cantidad

            iva_match = re.search(r'IVA\s+([0-9,.]+)', prefix, re.IGNORECASE)
            if iva_match:
                iva_str = iva_match.group(1).replace(',', '.')
                try:
                    iva_amount = float(iva_str)
                except ValueError:
                    pass

        results.append({
            'code': code,
            'unit_price': unit_price,
            'cantidad': cantidad,
            'subtotal': subtotal,
            'iva': iva_amount
        })

    return results