import os
from flask import Flask, request, jsonify
from neo4j import GraphDatabase
from googletrans import Translator

# Start the Flask app
app = Flask(__name__)
translator = Translator()

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD environment variable is not set. Do not store credentials in source code.")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Supported languages (Kenya + Sub-Saharan)
SUPPORTED_LANGS = [
    "sw",  # Swahili
    "so",  # Somali
    "am",  # Amharic
    "ha",  # Hausa
    "sn",  # Shona
    "zu",  # Zulu
    "xh",  # Xhosa
    "yo",  # Yoruba
    "ig",  # Igbo
    "af"   # Afrikaans
    # Kikuyu, Luo, Kamba, Maasai not yet supported by Google Translate
]

def soil_recommendation(pH, organic_matter):
    if pH < 5.5:
        return "Soil acidic, apply lime 2 bags/acre"
    elif organic_matter < 2.0:
        return "Low organic matter, add manure/compost"
    return "Use optimized fertilizer blend"

@app.route("/assess", methods=["POST"])
def assess_soil():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400

    farmer = data.get("farmer")
    location = data.get("location")
    pH = data.get("pH")
    organic_matter = data.get("organic_matter")
    lang = data.get("lang", "en")  # default English

    if farmer is None or location is None or pH is None or organic_matter is None:
        return jsonify({"error": "Missing required fields: farmer, location, pH, organic_matter."}), 400

    try:
        pH = float(pH)
        organic_matter = float(organic_matter)
    except (TypeError, ValueError):
        return jsonify({"error": "pH and organic_matter must be numeric values."}), 400

    # Generate English recommendation
    recommendation_en = soil_recommendation(pH, organic_matter)

    # Translate if supported
    recommendation_translated = None
    if lang in SUPPORTED_LANGS:
        try:
            recommendation_translated = translator.translate(recommendation_en, dest=lang).text
        except Exception:
            recommendation_translated = None

    # Save both versions in Neo4j
    with driver.session() as session:
        session.run(
            """
            MERGE (f:Farmer {name:$farmer})
            MERGE (l:Location {name:$location})
            MERGE (a:Assessment {pH:$pH, organic_matter:$organic_matter})
            MERGE (r:Recommendation {text_en:$text_en, text_translated:$text_translated, lang:$lang})
            MERGE (f)-[:LOCATED_IN]->(l)
            MERGE (f)-[:HAS_ASSESSMENT]->(a)
            MERGE (a)-[:LEADS_TO]->(r)
            """,
            farmer=farmer,
            location=location,
            pH=pH,
            organic_matter=organic_matter,
            text_en=recommendation_en,
            text_translated=recommendation_translated,
            lang=lang
        )

    # Return recommendation in the farmer’s language if available
    if recommendation_translated:
        return jsonify({"recommendation": recommendation_translated})
    else:
        return jsonify({"recommendation": recommendation_en})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
