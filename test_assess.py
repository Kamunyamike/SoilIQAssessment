from app import app

sample_payload = {
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
    "longitude": 36.0800,
}

if __name__ == "__main__":
    with app.test_client() as client:
        response = client.post("/assess", json=sample_payload)
        print("Status:", response.status_code)
        print(response.get_data(as_text=True))
