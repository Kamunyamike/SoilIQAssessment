# SoilIQ
SoilIQ is a field-friendly soil intelligence platform for extension officers and farmer-facing teams. The prototype combines rule-based agronomy, SoilGrids enrichment, Kenya soil policy guidance, and dual-language recommendations for practical soil health decisions.

## Project Overview
SoilIQ provides a Flask backend that accepts farmer inputs, soil observations, optional sensor readings, and a target language. It returns clear recommendations, confidence scores, policy-aligned explanations, and the triggered agronomic rules.

## Setup Instructions
### Clone the repository
```bash
git clone https://github.com/Kamunyamike/SoilIQAssessment.git
cd SoilIQAssessment
```

### Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Configure Neo4j connection
Set the Neo4j connection string and credentials before running the backend.

PowerShell:
```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="your_password_here"
```

Bash:
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password_here"
```

### Run the backend
```bash
python app.py
```
The backend listens on `http://0.0.0.0:5000` by default and supports deployment hosts.

## Deploy the backend for lovable.app
`https://soiliqassessment.lovable.app/` is currently live, but its `/assess` endpoint is not yet connected to your backend. Deploy the Flask app to a public HTTPS host and configure the lovable frontend to use that backend.

1. Deploy the backend to a public host such as Railway, Render, Fly.io, or another cloud provider.
2. Set these environment variables on the host:
   - `NEO4J_URI=bolt://localhost:7687` or your Neo4j connection string
   - `NEO4J_USER=neo4j`
   - `NEO4J_PASSWORD=<your_password>`
   - Optional: `AZURE_TRANSLATOR_KEY`, `AZURE_TRANSLATOR_REGION`
3. Confirm the backend is reachable via HTTPS.
4. Configure the lovable frontend to point at your deployed backend URL.
   - If the lovable app supports an environment variable, use `VITE_BACKEND_URL=https://your-backend-host`.
   - If it has a settings panel, enter the deployed backend address there.

If `https://soiliqassessment.lovable.app/` still shows the default placeholder, update the deployed frontend configuration to point to the backend URL and then test the `/assess` route with curl or Postman.

## Frontend Setup
### Install frontend dependencies
```bash
cd frontend
npm install
```

### Run the frontend
```bash
npm run dev
```
The frontend runs on `http://localhost:5173` by default.

### Configure frontend backend URL
Create a `.env` file in `frontend/` with:
```bash
VITE_BACKEND_URL=http://127.0.0.1:5000
```

## Dependencies
- Flask
- flask-cors
- neo4j
- requests
- googletrans
- React
- Vite
- Tailwind CSS

## API Usage
### Endpoint
`POST /assess`

### Example request JSON
```json
{
  "farmer": "Alice",
  "location": "Nakuru",
  "soil_color": "dark brown",
  "soil_texture": "loamy",
  "compaction": "firm",
  "pH": 5.4,
  "organic_matter": 2.8,
  "moisture": 22,
  "lang": "sw",
  "latitude": -0.3031,
  "longitude": 36.0800
}
```

### Example response JSON
```json
{
  "farmer": "Alice",
  "location": "Nakuru",
  "language": "sw",
  "soil_color": "dark brown",
  "soil_texture": "loamy",
  "compaction": "firm",
  "pH": 5.4,
  "organic_matter": 2.8,
  "moisture": 22,
  "fertility_zone": "medium",
  "policy_priority": "Improve soil health with organic inputs, lime, and blended fertilizer tailored to local crops.",
  "recommendation": "Tumia chokaa kwa kiwango kinachopendekezwa na ongeza nyenzo za kikaboni kuinua pH ya udongo. Ongeza samadi, komposti au mabaki ya mazao ili kuongeza nyenzo ya kikaboni kabla ya kutumia mbolea.",
  "recommendation_en": "Apply lime at recommended rates and add organic amendments to raise soil pH. Add manure, compost or crop residues to build organic matter before fertilizer application.",
  "recommendation_sw": "Tumia chokaa kwa kiwango kinachopendekezwa na ongeza nyenzo za kikaboni kuinua pH ya udongo. Ongeza samadi, komposti au mabaki ya mazao ili kuongeza nyenzo ya kikaboni kabla ya kutumia mbolea.",
  "confidence": 0.82,
  "triggered_rules": ["fertility_zone_medium", "pH<5.5", "organic_matter_low"],
  "sources": ["Kenya Soil Fertility Map 2020", "KALRO Fertilizer Recommendations", "FAO Visual Soil Assessment Guide", "USDA In-Field Soil Health Assessment Guide"],
  "explanation": "This recommendation is based on field observations, optional sensor readings, SoilGrids and Open-Meteo data, Kenyan soil policy guidance, and agronomic rules from KALRO, AGRA, FAO, USDA, and Gatsby.",
  "soilgrids": {
    "clay": 32.1,
    "sand": 45.7,
    "silt": 22.2,
    "organic_carbon": 1.2,
    "latitude": -0.3031,
    "longitude": 36.0800
  },
  "weather": {
    "temperature": 23.7,
    "wind_speed": 7.4,
    "precipitation": 0.0,
    "temp_max": 26.1,
    "temp_min": 18.9
  }
}
```

## Testing Instructions
Use Postman, curl, or any HTTP client to POST JSON to `/assess`.

Example curl:
```bash
curl -X POST http://127.0.0.1:5000/assess \
  -H "Content-Type: application/json" \
  -d '{"farmer":"Alice","location":"Nakuru","soil_color":"dark brown","soil_texture":"loamy","compaction":"firm","pH":5.4,"organic_matter":2.8,"moisture":22,"lang":"sw","latitude":-0.3031,"longitude":36.0800}'
```

## Neo4j Schema
The Neo4j graph stores:
- `(:Farmer)`
- `(:Location)`
- `(:Assessment)` with `pH`, `organic_matter`, and `created_at`
- `(:Recommendation)` with dual-language `text_en`, `text_sw`, `confidence`, and `created_at`
- `(Farmer)-[:LOCATED_IN]->(Location)`
- `(Farmer)-[:HAS_ASSESSMENT]->(Assessment)`
- `(Assessment)-[:GENERATED]->(Recommendation)`

### Seed example
Run `neo4j_schema.cypher` in Neo4j Browser or with `cypher-shell`:
```bash
cypher-shell -u neo4j -p your_password -f neo4j_schema.cypher
```

## Clustering Instructions
### Acidic low organic matter farms
```cypher
MATCH (a:Assessment)
WHERE a.pH < 5.5 AND a.organic_matter < 3
RETURN a.location AS location, a.farmer AS farmer, a.pH AS pH, a.organic_matter AS organic_matter;
```

### K-means clustering
```cypher
CALL gds.kmeans.stream({
  nodeProjection: 'Assessment',
  nodeProperties: ['pH', 'organic_matter'],
  k: 3
})
YIELD nodeId, clusterId
RETURN gds.util.asNode(nodeId).farmer AS farmer, gds.util.asNode(nodeId).location AS location, clusterId
ORDER BY clusterId, farmer;
```

### Persist cluster assignments
```cypher
CALL gds.kmeans.write({
  nodeProjection: 'Assessment',
  nodeProperties: ['pH', 'organic_matter'],
  k: 3,
  writeProperty: 'cluster_id'
})
YIELD nodePropertiesWritten, clusterCount, iterations;
```

## Responsible AI
- Recommendations use traceable agronomic sources and Kenyan policy guidance.
- Confidence values and triggered rules are returned for explainability.
- Privacy best practices: do not commit Neo4j credentials or translator keys to source control.
- The design is intended for extension officers and field staff, not laboratory-only workflows.
