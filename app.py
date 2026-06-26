import datetime
import logging
import os
import re
import requests
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS
from neo4j import GraphDatabase

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION")
AZURE_TRANSLATOR_ENDPOINT = os.getenv(
    "AZURE_TRANSLATOR_ENDPOINT",
    "https://api.cognitive.microsofttranslator.com",
)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

translator_headers = None
if AZURE_TRANSLATOR_KEY and AZURE_TRANSLATOR_REGION:
    translator_headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
    }
    app.logger.info("Azure Translator configured for SoilIQ translation.")
else:
    app.logger.info(
        "Azure Translator credentials are missing. Falling back to built-in Swahili mapping."
    )

SOIL_FERTILITY_MAP = {
    "nakuru": "medium",
    "uasin gishu": "high",
    "trans nzoia": "medium-low",
    "bungoma": "low",
    "nyandarua": "low-medium",
}

PRIORITY_RECOMMENDATION = {
    "high": "Focus on soil structure, organic carbon, and balanced fertilizer inputs according to Kenya Soil Fertility Map 2020.",
    "medium": "Improve soil health with organic inputs, lime, and blended fertilizer tailored to local crops.",
    "medium-low": "Strengthen moisture conservation, correct acidity, and use crops that build organic matter.",
    "low": "Correct soil acidity, build organic matter, and protect moisture through cover crops and mulch.",
    "unknown": "Use simple soil health steps before fertilizer application, focusing on cover, carbon, and structure.",
}

SUPPORTED_LANGS = [
    "en",
    "sw",
    "so",
    "am",
    "ha",
    "sn",
    "zu",
    "xh",
    "yo",
    "ig",
    "af",
]


def get_translator_url(path):
    return f"{AZURE_TRANSLATOR_ENDPOINT}{path}"


def detect_language(text):
    if not translator_headers or not text:
        return "en"
    try:
        response = requests.post(
            get_translator_url("/detect?api-version=3.0"),
            headers=translator_headers,
            json=[{"Text": text}],
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        if result and isinstance(result, list) and "language" in result[0]:
            return result[0]["language"]
    except Exception as exc:
        app.logger.warning("Azure detect_language failed: %s", exc)
    return "en"


def translate_text(text, dest, src=None):
    if not text or (dest == "en" and src == "en"):
        return text
    if translator_headers:
        try:
            params = {"api-version": "3.0", "to": dest}
            if src:
                params["from"] = src
            response = requests.post(
                get_translator_url("/translate"),
                params=params,
                headers=translator_headers,
                json=[{"Text": text}],
                timeout=10,
            )
            response.raise_for_status()
            translation = response.json()
            if translation and isinstance(translation, list):
                translations = translation[0].get("translations", [])
                if translations:
                    return translations[0].get("text", text)
        except Exception as exc:
            app.logger.warning("Azure translate_text failed: %s", exc)
    if dest == "en":
        return text
    translated = fallback_translate(text, dest)
    if translated != text:
        return translated
    try:
        from googletrans import Translator

        translator = Translator()
        return translator.translate(text, dest=dest, src=src or 'auto').text
    except Exception as exc:
        app.logger.warning("Fallback googletrans failed: %s", exc)
    return text


def fallback_translate(text, dest):
    if dest != "sw":
        return text

    fallback_map = {
        "Apply lime 2 bags/acre to raise soil pH": "Tumia chokaa vifungashio 2/eka kuinua pH ya udongo",
        "Apply elemental sulfur to lower soil pH": "Tumia sulfuri ya kimuundo ili kushusha pH ya udongo",
        "Add manure or compost to improve organic matter": "Ongeza samadi au komposti ili kuboresha nyenzo ya kikaboni",
        "Improve drainage and add organic matter for clay soils": "Boresha mifereji na ongeza nyenzo ya kikaboni kwa udongo wenye udongo mzito",
        "Use mulch and cover crops to conserve moisture in sandy soils": "Tumia mulch na mimea ya kufunika ili kuhifadhi unyevu katika udongo la mchanga",
        "Boost soil organic carbon with composted organic materials": "Ongeza kaboni ya kikaboni kwa udongo kwa kutumia vifaa vilivyokomaa",
        "Use optimized fertilizer blend based on local crop requirements": "Tumia mchanganyiko wa mbolea ulioboreshwa kwa mahitaji ya zao la eneo lako",
        "Reduce compaction with light tillage and deep-rooted legumes": "Punguza msongamano kwa kulima kwa mwanga na kupanda mimea yenye mizizi mirefu",
        "Protect moisture and use cover crops during dry spells": "Linda unyevu na tumia mimea ya kufunika wakati wa ukame",
        "Balance fertilizer based on soil testing and local crop needs": "Sawa mbolea kulingana na uchunguzi wa udongo na mahitaji ya zao la eneo lako",
    }

    translated = text
    for source_phrase, sw_phrase in fallback_map.items():
        translated = translated.replace(source_phrase, sw_phrase)
    return translated


def parse_coordinates(location):
    if not location or not isinstance(location, str):
        return None, None
    parts = re.split(r"\s*,\s*", location.strip())
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None, None
    return None, None


def fetch_soilgrids(location, latitude=None, longitude=None):
    lat = latitude
    lon = longitude
    if lat is None or lon is None:
        lat, lon = parse_coordinates(location)
    if lat is None or lon is None:
        return None

    url = f"https://rest.soilgrids.org/query?lon={lon}&lat={lat}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get("properties", {})
        layers = data.get("layers", {})
        soil_data = {}
        for key, layer in layers.items():
            if not layer or "values" not in layer:
                continue
            value = layer["values"][0].get("mean")
            if value is None:
                continue
            if key.startswith("clay"):
                soil_data["clay"] = value
            elif key.startswith("sand"):
                soil_data["sand"] = value
            elif key.startswith("silt"):
                soil_data["silt"] = value
            elif key.startswith("oc") or key.startswith("ocs") or "organic" in key:
                soil_data["organic_carbon"] = value
        if soil_data:
            soil_data["latitude"] = lat
            soil_data["longitude"] = lon
            return soil_data
    except Exception as exc:
        app.logger.warning("SoilGrids request failed: %s", exc)
    return None


def fetch_open_meteo(latitude, longitude):
    if latitude is None or longitude is None:
        return None

    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        "&current_weather=true&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Africa/Nairobi"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get("current_weather", {})
        daily = data.get("daily", {})
        return {
            "temperature": current.get("temperature"),
            "wind_speed": current.get("windspeed"),
            "precipitation": daily.get("precipitation_sum", [None])[0],
            "temp_max": daily.get("temperature_2m_max", [None])[0],
            "temp_min": daily.get("temperature_2m_min", [None])[0],
        }
    except Exception as exc:
        app.logger.warning("Open-Meteo request failed: %s", exc)
    return None


def lookup_kenya_soil_fertility(location):
    name = str(location).lower()
    for county, zone in SOIL_FERTILITY_MAP.items():
        if county in name:
            return zone
    return "unknown"


def build_soil_recommendation(
    soil_color,
    soil_texture,
    compaction,
    pH,
    organic_matter,
    moisture,
    soil_data=None,
    fertility_zone=None,
    weather=None,
):
    rules = []
    sources = []
    recommendations = []
    confidence = 0.64

    if fertility_zone:
        recommendations.append(PRIORITY_RECOMMENDATION.get(fertility_zone, PRIORITY_RECOMMENDATION["unknown"]))
        rules.append(f"fertility_zone_{fertility_zone}")
        sources.append("Kenya Soil Fertility Map 2020")
        confidence += 0.04

    if pH is not None:
        if pH < 5.5:
            recommendations.append("Apply lime at recommended rates and add organic amendments to raise soil pH.")
            rules.append("pH<5.5")
            sources.append("KALRO Fertilizer Recommendations")
            sources.append("Gatsby Africa Lime Report")
            confidence += 0.10
        elif pH < 6.5:
            recommendations.append("Monitor pH and maintain soil health with cover crops before additional fertilizer.")
            rules.append("pH_5.5_6.5")
            sources.append("KALRO Fertilizer Recommendations")
            confidence += 0.05
        elif pH > 7.5:
            recommendations.append("Apply elemental sulfur carefully and avoid over-alkaline fertilizer blends.")
            rules.append("pH>7.5")
            sources.append("KALRO Fertilizer Recommendations")
            confidence += 0.08
        else:
            recommendations.append("Soil pH is acceptable; focus on organic matter and soil structure.")
            rules.append("pH_optimal")
            confidence += 0.04

    if organic_matter is not None:
        if organic_matter < 3.0:
            recommendations.append("Add manure, compost or crop residues to build organic matter before fertilizer application.")
            rules.append("organic_matter_low")
            sources.append("FAO Visual Soil Assessment Guide")
            sources.append("USDA In-Field Soil Health Assessment Guide")
            confidence += 0.08
        elif organic_matter >= 5.0:
            recommendations.append("Organic matter is healthy; maintain residue cover and balanced nutrients.")
            rules.append("organic_matter_good")
            confidence += 0.04

    if moisture is not None:
        if moisture < 25:
            recommendations.append("Use mulch, cover crops and simple basins to conserve moisture during dry periods.")
            rules.append("low_moisture")
            sources.append("Kenya Meteorological Department agrometeorology")
            confidence += 0.08
        elif moisture > 60:
            recommendations.append("Improve drainage and avoid compaction when soil is too wet.")
            rules.append("high_moisture")
            sources.append("USDA In-Field Soil Health Assessment Guide")
            confidence += 0.05

    if soil_texture:
        texture = soil_texture.lower()
        if "clay" in texture:
            recommendations.append("Clay soil needs organic matter, good drainage, and protection from compaction.")
            rules.append("soil_texture_clay")
            sources.append("FAO Visual Soil Assessment Guide")
            confidence += 0.06
        elif "sandy" in texture:
            recommendations.append("Sandy soil benefits from mulch and frequent organic additions to retain moisture.")
            rules.append("soil_texture_sandy")
            sources.append("AGRA Fertilizer Blends Report")
            confidence += 0.06
        elif "loam" in texture:
            recommendations.append("Loamy soil is balanced; keep residue cover and use blended fertilizer conservatively.")
            rules.append("soil_texture_loamy")
            confidence += 0.04

    if compaction:
        compact_value = compaction.lower()
        if compact_value in ("compact", "very compact"):
            recommendations.append("Reduce compaction with light tillage and deep-rooted legumes.")
            rules.append("soil_compaction")
            sources.append("USDA In-Field Soil Health Assessment Guide")
            confidence += 0.07
        elif compact_value == "firm":
            recommendations.append("Avoid heavy traffic and keep the soil surface covered to improve structure.")
            rules.append("soil_compaction_firm")
            confidence += 0.04

    if soil_color:
        color = soil_color.lower()
        if "grey" in color:
            recommendations.append("Grey color may signal poor drainage; improve structure and cover the soil.")
            rules.append("soil_color_grey")
            sources.append("FAO Visual Soil Assessment Guide")
            confidence += 0.05
        elif "yellow" in color:
            recommendations.append("Yellowish soil may need more organic matter and moisture retention.")
            rules.append("soil_color_yellow")
            confidence += 0.04
        elif "dark" in color or "black" in color:
            recommendations.append("Dark soil is promising; continue adding organics and avoid erosion.")
            rules.append("soil_color_dark")
            confidence += 0.03

    if soil_data:
        clay = soil_data.get("clay")
        sand = soil_data.get("sand")
        oc = soil_data.get("organic_carbon")
        if oc is not None and oc < 1.0:
            recommendations.append("Boost soil organic carbon with compost and cover crops.")
            rules.append("soilgrids_low_oc")
            sources.append("SoilGrids API")
            confidence += 0.06
        if clay is not None and clay >= 35:
            recommendations.append("High clay content means improve drainage and avoid surface sealing.")
            if "soil_texture_clay" not in rules:
                rules.append("soilgrids_clay")
            confidence += 0.04
        if sand is not None and sand >= 60:
            recommendations.append("Sandy texture needs extra mulch and organic matter to conserve moisture.")
            if "soil_texture_sandy" not in rules:
                rules.append("soilgrids_sand")
            confidence += 0.04

    if weather:
        precipitation = weather.get("precipitation")
        if precipitation is not None and precipitation < 2:
            recommendations.append("Local forecast is dry; prioritize moisture conservation.")
            rules.append("weather_dry")
            sources.append("Open-Meteo + KMD agrometeorology")
            confidence += 0.03
        temperature = weather.get("temperature")
        if temperature is not None and temperature > 30:
            recommendations.append("High temperature means keep soil covered and avoid crusting.")
            rules.append("weather_hot")
            confidence += 0.03

    if not recommendations:
        recommendations.append("Take simple soil health actions first: cover the soil, build organic matter, and then use balanced fertilizer.")
        rules.append("default_soil_health")
        sources.append("Agricultural Soil Management Policy 2023")
        confidence = 0.66

    unique_sources = list(dict.fromkeys(sources))
    explanation = (
        "This recommendation is based on field observations, optional sensor readings, SoilGrids and Open-Meteo data, Kenyan soil policy guidance, and agronomic rules from KALRO, AGRA, FAO, USDA, and Gatsby."
    )
    return (
        " ".join(recommendations).strip(),
        rules,
        unique_sources,
        min(confidence, 0.94),
        explanation,
    )


def enrich_location(location):
    detected = detect_language(location)
    if detected != "en":
        return translate_text(location, dest="en", src=detected)
    return location


driver = None
if NEO4J_PASSWORD:
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        app.logger.info("Connected to Neo4j.")
    except Exception as exc:
        app.logger.warning("Neo4j initialization failed: %s", exc)
        driver = None
else:
    app.logger.info("NEO4J_PASSWORD is not set; Neo4j writes are disabled.")


def save_assessment_to_neo4j(
    farmer,
    farmer_en,
    location,
    location_en,
    soil_color,
    soil_texture,
    compaction,
    pH,
    moisture,
    organic_matter,
    recommendation_en,
    recommendation_sw,
    confidence,
    triggered_rules,
    sources,
    soil_data=None,
    fertility_zone=None,
    policy_priority=None,
    weather=None,
):
    if not driver:
        app.logger.info("Neo4j driver is unavailable; skipping graph write.")
        return

    assessment_id = str(uuid.uuid4())
    recommendation_id = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()

    with driver.session() as session:
        session.run(
            """
            MERGE (f:Farmer {name:$farmer})
            SET f.name_en = $farmer_en
            MERGE (l:Location {name:$location})
            SET l.name_en = $location_en
            CREATE (a:Assessment {
                id:$assessment_id,
                soil_color:$soil_color,
                soil_texture:$soil_texture,
                compaction:$compaction,
                pH:$pH,
                moisture:$moisture,
                organic_matter:$organic_matter,
                soil_fertility_zone:$fertility_zone,
                policy_priority:$policy_priority,
                soilgrids_oc:$soilgrids_oc,
                created_at:$created_at
            })
            CREATE (r:Recommendation {
                id:$recommendation_id,
                text_en:$text_en,
                text_sw:$text_sw,
                confidence:$confidence,
                triggered_rules:$triggered_rules,
                sources:$sources,
                created_at:$created_at
            })
            MERGE (f)-[:LOCATED_IN]->(l)
            MERGE (f)-[:HAS_ASSESSMENT]->(a)
            MERGE (a)-[:GENERATED]->(r)
            """,
            farmer=farmer,
            farmer_en=farmer_en,
            location=location,
            location_en=location_en,
            assessment_id=assessment_id,
            soil_color=soil_color,
            soil_texture=soil_texture,
            compaction=compaction,
            pH=pH,
            moisture=moisture,
            organic_matter=organic_matter,
            fertility_zone=fertility_zone,
            policy_priority=policy_priority,
            soilgrids_oc=soil_data.get("organic_carbon") if soil_data else None,
            created_at=created_at,
            recommendation_id=recommendation_id,
            text_en=recommendation_en,
            text_sw=recommendation_sw,
            confidence=confidence,
            triggered_rules=triggered_rules,
            sources=sources,
        )


@app.route("/assess", methods=["POST"])
def assess():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400

    farmer = data.get("farmer")
    location = data.get("location")
    soil_color = data.get("soil_color") or data.get("color")
    soil_texture = data.get("soil_texture") or data.get("texture")
    compaction = data.get("compaction")
    pH = data.get("pH")
    organic_matter = data.get("organic_matter")
    moisture = data.get("moisture")
    lang = str(data.get("lang", "en")).lower()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not farmer or not location or not soil_color or not soil_texture or not compaction:
        return jsonify(
            {
                "error": "Missing required fields: farmer, location, soil_color, soil_texture, compaction."
            }
        ), 400

    if lang not in SUPPORTED_LANGS:
        lang = "en"

    try:
        pH = float(pH) if pH is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "pH must be a numeric value if provided."}), 400

    try:
        organic_matter = float(organic_matter) if organic_matter is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "organic_matter must be a numeric value if provided."}), 400

    try:
        moisture = float(moisture) if moisture is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "moisture must be a numeric value if provided."}), 400

    try:
        if latitude is not None and longitude is not None:
            latitude = float(latitude)
            longitude = float(longitude)
    except (TypeError, ValueError):
        latitude = None
        longitude = None

    farmer_en = enrich_location(str(farmer))
    location_en = enrich_location(str(location))
    soil_data = fetch_soilgrids(str(location), latitude, longitude)
    weather_data = fetch_open_meteo(latitude, longitude)
    fertility_zone = lookup_kenya_soil_fertility(location)
    policy_priority = PRIORITY_RECOMMENDATION.get(fertility_zone, PRIORITY_RECOMMENDATION["unknown"])

    recommendation_en, triggered_rules, sources, confidence, explanation = build_soil_recommendation(
        soil_color,
        soil_texture,
        compaction,
        pH,
        organic_matter,
        moisture,
        soil_data=soil_data,
        fertility_zone=fertility_zone,
        weather=weather_data,
    )
    recommendation_sw = translate_text(recommendation_en, dest="sw")
    recommendation = recommendation_en if lang == "en" else translate_text(recommendation_en, dest=lang)

    save_assessment_to_neo4j(
        farmer=str(farmer),
        farmer_en=farmer_en,
        location=str(location),
        location_en=location_en,
        soil_color=soil_color,
        soil_texture=soil_texture,
        compaction=compaction,
        pH=pH,
        moisture=moisture,
        organic_matter=organic_matter,
        recommendation_en=recommendation_en,
        recommendation_sw=recommendation_sw,
        confidence=confidence,
        triggered_rules=triggered_rules,
        sources=sources,
        soil_data=soil_data,
        fertility_zone=fertility_zone,
        policy_priority=policy_priority,
        weather=weather_data,
    )

    return jsonify(
        {
            "farmer": farmer,
            "location": location,
            "language": lang,
            "soil_color": soil_color,
            "soil_texture": soil_texture,
            "compaction": compaction,
            "pH": pH,
            "organic_matter": organic_matter,
            "moisture": moisture,
            "fertility_zone": fertility_zone,
            "policy_priority": policy_priority,
            "recommendation": recommendation,
            "recommendation_en": recommendation_en,
            "recommendation_sw": recommendation_sw,
            "confidence": confidence,
            "triggered_rules": triggered_rules,
            "sources": sources,
            "explanation": explanation,
            "soilgrids": soil_data,
            "weather": weather_data,
        }
    )


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=True)
