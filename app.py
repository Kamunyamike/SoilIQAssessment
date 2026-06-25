import os

from flask import Flask, request, jsonify
from neo4j import GraphDatabase

# Start the Flask app
app = Flask(__name__)

# Neo4j connection settings for local AuraGDS instance
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "REDACTED_NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Simple rule-based function

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

    if farmer is None or location is None or pH is None or organic_matter is None:
        return jsonify({"error": "Missing required fields: farmer, location, pH, organic_matter."}), 400

    try:
        pH = float(pH)
        organic_matter = float(organic_matter)
    except (TypeError, ValueError):
        return jsonify({"error": "pH and organic_matter must be numeric values."}), 400

    recommendation = soil_recommendation(pH, organic_matter)

    with driver.session() as session:
        session.run(
            """
            MERGE (f:Farmer {name:$farmer})
            MERGE (l:Location {name:$location})
            MERGE (a:Assessment {pH:$pH, organic_matter:$organic_matter})
            MERGE (r:Recommendation {text:$recommendation})
            MERGE (f)-[:LOCATED_IN]->(l)
            MERGE (f)-[:HAS_ASSESSMENT]->(a)
            MERGE (a)-[:LEADS_TO]->(r)
            """,
            farmer=farmer,
            location=location,
            pH=pH,
            organic_matter=organic_matter,
            recommendation=recommendation,
        )

    return jsonify({"recommendation": recommendation})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
