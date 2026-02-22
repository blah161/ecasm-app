# ecasm_compiler.py — rule-based CASM → normalized output

def compile_ecasm_code(source: str) -> str:
    """
    Take CASM / quantum-like input and normalize it into
    a stable, readable form. Supports:
      - MOV R1, 5
      - ADD R3, R1, R2
      - IF R3 > 12 GOTO 10
      - LABEL 10
      - X Q0
      - H Q1
      - CX Q0, Q1
      - MEASURE Q1 -> C0
    Everything else → UNKNOWN INSTRUCTION: ...
    """
    lines = source.splitlines()
    output = []
    labels = set()

    # -------- pass 1: collect label names --------
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("LABEL "):
            _, name = line.split(None, 1)
            labels.add(name.strip())

    # -------- pass 2: compile --------
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        up = line.upper()

        # MOV R1, 5
        if up.startswith("MOV "):
            try:
                _, rest = line.split(None, 1)
                left, right = [x.strip() for x in rest.split(",", 1)]
                output.append(f"SET {left} ⇐ {right}")
            except Exception:
                output.append(f"UNKNOWN INSTRUCTION: {raw}")
            continue

        # ADD R3, R1, R2
        if up.startswith("ADD "):
            try:
                _, rest = line.split(None, 1)
                parts = [p.strip() for p in rest.split(",")]
                dest, op1, op2 = parts
                output.append(f"{dest} ⇐ {op1} + {op2}")
            except Exception:
                output.append(f"UNKNOWN INSTRUCTION: {raw}")
            continue

        # IF R3 > 12 GOTO 10
        if up.startswith("IF ") and " GOTO " in up:
            try:
                cond_part, label_part = line.split("GOTO", 1)
                cond_part = cond_part.strip()[3:]  # drop "IF "
                label = label_part.strip()
                output.append(f"IF {cond_part} THEN → {label}")
            except Exception:
                output.append(f"UNKNOWN INSTRUCTION: {raw}")
            continue

        # LABEL 10
        if up.startswith("LABEL "):
            label = line.split(None, 1)[1].strip()
            output.append(f"[{label}]:")
            continue

        # X Q0
        if up.startswith("X "):
            q = line.split(None, 1)[1].strip()
            output.append(f"X({q})")
            continue

        # H Q1
        if up.startswith("H "):
            q = line.split(None, 1)[1].strip()
            output.append(f"H({q})")
            continue

        # CX Q0, Q1
        if up.startswith("CX "):
            try:
                _, rest = line.split(None, 1)
                c, t = [p.strip() for p in rest.split(",", 1)]
                output.append(f"CX({c}, {t})")
            except Exception:
                output.append(f"UNKNOWN INSTRUCTION: {raw}")
            continue

        # MEASURE Q1 -> C0
        if up.startswith("MEASURE "):
            try:
                before, after = line.split("->", 1)
                q = before.split(None, 1)[1].strip()
                c = after.strip()
                output.append(f"{q} ⇨ {c}  [MEASURE]")
            except Exception:
                output.append(f"UNKNOWN INSTRUCTION: {raw}")
            continue

        # anything else
        output.append(f"UNKNOWN INSTRUCTION: {raw}")

    return "\n".join(output)