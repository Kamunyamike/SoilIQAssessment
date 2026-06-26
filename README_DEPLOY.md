# SoilIQ Deployment Guide

## Backend Deployment

Use one of these options:

### Option 1: Deploy with Docker

1. Build the image:
   ```bash
   docker build -t soiliq-backend .
   ```
2. Run the container:
   ```bash
   docker run -e NEO4J_URI="bolt://your-neo4j-host:7687" \
     -e NEO4J_USER="neo4j" \
     -e NEO4J_PASSWORD="your_password" \
     -e FLASK_RUN_HOST="0.0.0.0" \
     -e FLASK_RUN_PORT="5000" \
     -p 5000:5000 \
     soiliq-backend
   ```

### Option 2: Deploy to Railway / Render / Fly.io

- Set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Optionally set `AZURE_TRANSLATOR_KEY`, `AZURE_TRANSLATOR_REGION`
- Set `FLASK_RUN_HOST=0.0.0.0`
- Set `FLASK_RUN_PORT=5000`

## Frontend Deployment

### Option 1: Netlify

1. Connect the `frontend/` folder as a Netlify site.
2. Set the build command: `npm install && npm run build`
3. Set the publish directory: `dist`
4. Set environment variable:
   - `VITE_BACKEND_URL=https://your-backend-host`

### Option 2: Vercel

- Set the project root to `frontend/`
- Set `Framework Preset` to `Vite`
- Set environment variable:
  - `VITE_BACKEND_URL=https://your-backend-host`

## lovable.app Integration

If lovable.app supports a frontend URL or runtime JS override, set the backend to:
- `window.__BACKEND_URL__ = "https://your-backend-host"`
- or `window.BACKEND_URL = "https://your-backend-host"`
- or `VITE_BACKEND_URL=https://your-backend-host`

## Testing

Test the backend:
```bash
curl -X POST https://your-backend-host/assess \
  -H "Content-Type: application/json" \
  -d '{"farmer":"Alice","location":"Nakuru","soil_color":"dark brown","soil_texture":"loamy","compaction":"firm","pH":5.4,"organic_matter":2.8,"moisture":22,"lang":"sw","latitude":-0.3031,"longitude":36.0800}'
```

Test the frontend by visiting the deployed frontend and submitting the assessment form.
