# deploy bump: documentation update
from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
import re
import os
import json
import uuid
app = Flask(__name__)
# -------------------------------
# FREE COMPILE LIMIT CONFIG
# -------------------------------

FREE_COMPILE_LIMIT = 5


def load_usage():
    if not os.path.exists(USAGE_FILE):
        return {}
    with open(USAGE_FILE, "r") as f:
        return json.load(f)


def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)


def get_client_id():
    """
    Simple client identifier.
    For now, use IP address.
    (Good enough for v1; can upgrade later.)
    """
    return request.remote_addr


def increment_compile_count():
    usage = load_usage()
    client_id = get_client_id()

    count = usage.get(client_id, 0) + 1
    usage[client_id] = count
    save_usage(usage)

    return count

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BUYERS_FILE = os.path.join(BASE_DIR, "buyers.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
RESETS_FILE = os.path.join(BASE_DIR, "resets.json")
USAGE_FILE = os.path.join(BASE_DIR, "usage.json")

# Ensure usage store exists
if not os.path.exists(USAGE_FILE):
    with open(USAGE_FILE, "w") as f:
        json.dump({}, f)

# Ensure persistent data stores exist
for fp in [BUYERS_FILE, USERS_FILE, RESETS_FILE]:
    if not os.path.exists(fp):
        with open(fp, "w") as f:
            json.dump({}, f)


# -------------------------------
# VALIDATION RULES (CASM / Quantum)
# -------------------------------

VALID_OPCODES = {"X", "H", "CX", "MEASURE"}
VALID_TARGET = re.compile(r"^[QC][0-9]+$")


def validate_line(line):
    parts = line.strip().split()
    if not parts:
        return False, "Empty line"

    op = parts[0]

    if op not in VALID_OPCODES:
        return False, f"Unknown opcode '{op}'"

    # MEASURE Q1 -> C0
    if op == "MEASURE":
        if len(parts) != 4 or parts[2] != "->":
            return False, "Invalid MEASURE syntax (expected: MEASURE Q1 -> C0)"

        if not VALID_TARGET.match(parts[1]):
            return False, f"Invalid quantum register '{parts[1]}'"

        if not VALID_TARGET.match(parts[3]):
            return False, f"Invalid classical register '{parts[3]}'"

        return True, None

    # X/H/CX register validation
    for arg in parts[1:]:
        if not VALID_TARGET.match(arg):
            return False, f"Invalid register '{arg}'"

    return True, None


def format_compiled_output(lines):
    formatted = []
    for i, line in enumerate(lines, start=1):
        formatted.append(f"{i:02d} │ {line}")
    return "\n".join(formatted)


# -------------------------------
# ROUTES
# -------------------------------
@app.route("/")
def landing():
    resp = make_response(render_template("landing.html"))

    # Create anonymous user id if missing
    if not request.cookies.get("ecasm_uid"):
        anon_id = str(uuid.uuid4())
        resp.set_cookie(
            "ecasm_uid",
            anon_id,
            max_age=60 * 60 * 24 * 365,  # 1 year
            httponly=True,
            samesite="Lax"
        )

    return resp


@app.route("/compile", methods=["POST"])
def compile_code():
    # --- enforce free compile limit ---
    uid = request.cookies.get("ecasm_uid")
    if not uid:
        return jsonify({
            "ok": False,
            "errors": ["Session not initialized. Please refresh the page."]
        })

    usage = load_usage()
    count = usage.get(uid, 0)

    if count >= FREE_COMPILE_LIMIT:
        return jsonify({
            "ok": False,
            "errors": ["Free compile limit reached (5 compiles). Please register to continue."],
            "limit_reached": True
        })

    # --- increment usage ---
    usage[uid] = count + 1
    save_usage(usage)

    # --- normal compile logic ---
    code = request.json.get("code", "")
    raw_lines = [l for l in code.split("\n") if l.strip()]
    errors = []

    for line in raw_lines:
        ok, msg = validate_line(line)
        if not ok:
            errors.append(msg)

    if errors:
        return jsonify({"ok": False, "errors": errors})

    compiled = format_compiled_output(raw_lines)
    return jsonify({"ok": True, "compiled_output": compiled})


@app.route("/emit", methods=["POST"])
def emit_code():
    code = request.json.get("code", "")
    raw_lines = [l for l in code.split("\n") if l.strip()]

    output_lines = []
    for i, line in enumerate(raw_lines, start=1):
        output_lines.append(f"[{i:02d}] Executing → {line}")

    output_lines.append("✔ Emission complete.")
    return jsonify({"emission": "\n".join(output_lines)})


@app.route("/register_license", methods=["POST"])
def register_license():
    """
    Your actual license validation logic lives in PythonAnywhere.
    For the Render GUI version, we simply acknowledge the key.
    """
    data = request.json
    key = (data.get("license_key") or "").strip()

    if key == "":
        return jsonify({"ok": False, "message": "License key required."})

    # Placeholder behavior — no remote validation done here
    return jsonify({"ok": True, "message": "License accepted."})

@app.route("/documentation")
def documentation():
    return redirect(url_for("static", filename="documentation.html"))


@app.route("/eula")
def eula():
    return render_template("eula.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/compiler")
def compiler():
    return render_template("index.html")

@app.route("/ecasmcompiler.html")
@app.route("/ecasm-compiler.html")
def legacy_compiler_redirect():
    return redirect(url_for("compiler"), code=301)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)