from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------- /generate-estimate ----------
@app.route('/generate-estimate', methods=['POST'])
def generate_estimate():
    data = request.get_json()

    square_feet = data.get("squareFeet", 0)
    outlet_count = data.get("outletCount", 0)
    lighting_count = data.get("lightingFixtureCount", 0)
    switch_count = data.get("switchCount", 0)
    panel_count = data.get("panelCount", 0)
    emt_conduit_feet = data.get("emtConduitFeet", 0)

    materials = [
        {"name": "Duplex outlet", "quantity": outlet_count, "unit": "each"},
        {"name": "Lighting fixture", "quantity": lighting_count, "unit": "each"},
        {"name": "Single pole switch", "quantity": switch_count, "unit": "each"},
        {"name": "Electrical panel", "quantity": panel_count, "unit": "each"},
        {"name": "EMT conduit", "quantity": emt_conduit_feet, "unit": "feet"},
        {"name": "12AWG THHN wire", "quantity": outlet_count * 50, "unit": "feet"}
    ]

    labor_hours = (
        outlet_count * 0.5 +
        lighting_count * 0.75 +
        switch_count * 0.3 +
        panel_count * 8 +
        (emt_conduit_feet / 20)
    )

    result = {
        "materials": materials,
        "laborHours": round(labor_hours, 1),
        "assumptions": "Estimated using NEC-based commercial rules."
    }

    return jsonify(result)


# ---------- /analyze-drawing ----------
def extract_scales_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    results = []

    scale_pattern = re.compile(r'scale[:\s]*([^\n]+)', re.IGNORECASE)

    for page_number in range(len(doc)):
        page = doc[page_number]
        text = page.get_text()
        match = scale_pattern.search(text)
        if match:
            scale_value = match.group(1).strip()
        else:
            scale_value = "Not found"

        results.append({
            "page": page_number + 1,
            "scale": scale_value
        })

    return results


@app.route('/analyze-drawing', methods=['POST'])
def analyze_drawing():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        scales = extract_scales_from_pdf(file_path)
        return jsonify({
            "sheetScales": scales,
            "message": "Drawing scale extraction complete."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Start Server ----------
if __name__ == '__main__':
    app.run(debug=True)
