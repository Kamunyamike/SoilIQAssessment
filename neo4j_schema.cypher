// SoilIQ Neo4j schema and seed data for the CGA/FTMA Soil Health Assessment prototype

// 1. Schema constraints
CREATE CONSTRAINT unique_farmer_name IF NOT EXISTS
ON (f:Farmer) ASSERT f.name IS UNIQUE;

CREATE CONSTRAINT unique_location_name IF NOT EXISTS
ON (l:Location) ASSERT l.name IS UNIQUE;

CREATE CONSTRAINT unique_assessment_id IF NOT EXISTS
ON (a:Assessment) ASSERT a.id IS UNIQUE;

CREATE CONSTRAINT unique_recommendation_id IF NOT EXISTS
ON (r:Recommendation) ASSERT r.id IS UNIQUE;

// 2. Example seed for one farmer in Nakuru
MERGE (f:Farmer {name: 'Nakuru Farmer 1'})
SET f.name_en = 'Nakuru Farmer 1'
MERGE (l:Location {name: 'Nakuru'})
SET l.name_en = 'Nakuru'
CREATE (a:Assessment {
  id: 'assessment-0001',
  pH: 5.2,
  organic_matter: 2.6,
  soil_texture: 'loamy',
  soilgrids_oc: 1.1,
  created_at: datetime()
})
CREATE (r:Recommendation {
  id: 'recommendation-0001',
  text_en: 'Apply lime at recommended rates and add organic amendments to raise soil pH. Add manure or compost to build organic matter.',
  text_sw: 'Tumia chokaa kwa kiwango kinachopendekezwa na ongeza nyenzo za kikaboni kuinua pH ya udongo. Ongeza samadi au komposti kuongeza nyenzo ya kikaboni.',
  created_at: datetime(),
  confidence: 0.86,
  triggered_rules: ['pH<5.5', 'organic_matter_low']
})
MERGE (f)-[:LOCATED_IN]->(l)
MERGE (f)-[:HAS_ASSESSMENT]->(a)
MERGE (a)-[:GENERATED]->(r);

// 3. Example synthetic seed data for 10 Kenyan farms
WITH [
  {farm:'Nakuru Farm 2', location:'Nakuru', pH:6.3, om:3.8, texture:'sandy', oc:0.9, rules:['soil_texture_sandy','soilgrids_low_oc']},
  {farm:'Uasin Gishu Farm 1', location:'Eldoret', pH:6.8, om:4.5, texture:'loamy', oc:1.8, rules:['organic_matter_good']},
  {farm:'Uasin Gishu Farm 2', location:'Eldoret', pH:5.6, om:2.4, texture:'clay', oc:1.0, rules:['pH_5.5_6.5','soil_texture_clay']},
  {farm:'Trans Nzoia Farm 1', location:'Kitale', pH:5.1, om:1.9, texture:'sandy loam', oc:0.8, rules:['pH<5.5','soilgrids_low_oc']},
  {farm:'Trans Nzoia Farm 2', location:'Kitale', pH:7.8, om:3.1, texture:'silty', oc:1.2, rules:['pH>7.5']},
  {farm:'Bungoma Farm 1', location:'Kimilili', pH:4.9, om:2.1, texture:'clay', oc:0.7, rules:['pH<5.5','soil_texture_clay','soilgrids_low_oc']},
  {farm:'Bungoma Farm 2', location:'Kimilili', pH:6.0, om:2.9, texture:'loam', oc:1.0, rules:['pH_5.5_6.5']},
  {farm:'Nyandarua Farm 1', location:'Ndaragua', pH:5.4, om:1.7, texture:'silty', oc:0.6, rules:['pH<5.5','organic_matter_low']},
  {farm:'Nyandarua Farm 2', location:'Ndaragua', pH:6.2, om:3.4, texture:'loamy', oc:1.4, rules:['organic_matter_good']}
] AS farms
UNWIND farms AS farmData
MERGE (f:Farmer {name: farmData.farm})
SET f.name_en = farmData.farm
MERGE (l:Location {name: farmData.location})
SET l.name_en = farmData.location
CREATE (a:Assessment {
  id: randomUUID(),
  pH: farmData.pH,
  organic_matter: farmData.om,
  soil_texture: farmData.texture,
  soilgrids_oc: farmData.oc,
  created_at: datetime()
})
CREATE (r:Recommendation {
  id: randomUUID(),
  text_en: 'Soil assessment findings indicate targeted soil health actions for this location.',
  text_sw: 'Matokeo ya tathmini ya udongo yanaonyesha hatua maalum za afya ya udongo kwa eneo hili.',
  created_at: datetime(),
  confidence: 0.78,
  triggered_rules: farmData.rules
})
MERGE (f)-[:LOCATED_IN]->(l)
MERGE (f)-[:HAS_ASSESSMENT]->(a)
MERGE (a)-[:GENERATED]->(r);

// 4. Dual-language recommendation query example
MATCH (f:Farmer)-[:HAS_ASSESSMENT]->(a:Assessment)-[:GENERATED]->(r:Recommendation)
RETURN f.name AS farmer, a.location AS location, r.text_en AS recommendation_en, r.text_sw AS recommendation_sw, r.confidence AS confidence, r.triggered_rules AS triggered_rules
LIMIT 20;

// 5. Query farms with acid soils and low organic matter
MATCH (a:Assessment)
WHERE a.pH < 5.5 AND a.organic_matter < 3
RETURN a.location AS location, a.farmer AS farmer, a.pH AS pH, a.organic_matter AS organic_matter;

// 6. K-means clustering using GDS
CALL gds.kmeans.stream({
  nodeProjection: 'Assessment',
  nodeProperties: ['pH', 'organic_matter'],
  k: 3
})
YIELD nodeId, clusterId
RETURN gds.util.asNode(nodeId).farmer AS farmer, gds.util.asNode(nodeId).location AS location, clusterId
ORDER BY clusterId, farmer;

// 7. Write cluster assignments back to the graph
CALL gds.kmeans.write({
  nodeProjection: 'Assessment',
  nodeProperties: ['pH', 'organic_matter'],
  k: 3,
  writeProperty: 'cluster_id'
})
YIELD nodePropertiesWritten, clusterCount, iterations;
