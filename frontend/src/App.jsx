import { useState } from 'react';

const defaultPayload = {
  farmer: '',
  location: '',
  soil_color: 'dark brown',
  soil_texture: 'loamy',
  compaction: 'firm',
  pH: 5.5,
  organic_matter: 3.0,
  moisture: 25,
  lang: 'en',
  latitude: '',
  longitude: '',
};

const colors = ['dark brown', 'brown', 'yellow', 'grey', 'black'];
const textures = ['loamy', 'sandy', 'clay', 'silty', 'sandy loam'];
const compactions = ['soft', 'firm', 'compact', 'very compact'];
const languages = [
  { value: 'en', label: 'English' },
  { value: 'sw', label: 'Swahili' },
  { value: 'so', label: 'Somali' },
  { value: 'ha', label: 'Hausa' },
];

function App() {
  const [payload, setPayload] = useState(defaultPayload);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const onChange = (key, value) => {
    setPayload((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setResponse(null);
    setLoading(true);

    try {
      const runtimeBackendUrl =
        window?.__BACKEND_URL__ || window?.BACKEND_URL || window?.REACT_APP_BACKEND_URL;
      const backendBaseUrl =
        import.meta.env.VITE_BACKEND_URL || runtimeBackendUrl || 'http://127.0.0.1:5000';
      const backendUrl = backendBaseUrl.endsWith('/assess')
        ? backendBaseUrl
        : `${backendBaseUrl.replace(/\/+$|\s+$/g, '')}/assess`;
      const res = await fetch(backendUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Backend error');
      }
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="mx-auto max-w-4xl rounded-3xl border border-slate-200 bg-white p-8 shadow-md">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-slate-900">SoilIQ Assessment</h1>
          <p className="mt-2 text-slate-600">
            A field-friendly soil health assessment form for extension officers. Enter farmer details, soil observations, optional sensor inputs, and get a practical recommendation.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Farmer name</span>
              <input
                type="text"
                value={payload.farmer}
                onChange={(event) => onChange('farmer', event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                required
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Location</span>
              <input
                type="text"
                value={payload.location}
                onChange={(event) => onChange('location', event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                required
              />
            </label>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Soil color</span>
              <select
                value={payload.soil_color}
                onChange={(event) => onChange('soil_color', event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
              >
                {colors.map((color) => (
                  <option key={color} value={color}>{color}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Soil texture</span>
              <select
                value={payload.soil_texture}
                onChange={(event) => onChange('soil_texture', event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
              >
                {textures.map((texture) => (
                  <option key={texture} value={texture}>{texture}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Compaction</span>
              <select
                value={payload.compaction}
                onChange={(event) => onChange('compaction', event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
              >
                {compactions.map((compaction) => (
                  <option key={compaction} value={compaction}>{compaction}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">pH</span>
              <input
                type="number"
                step="0.1"
                value={payload.pH}
                onChange={(event) => onChange('pH', Number(event.target.value))}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                min="3"
                max="9"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Organic matter (%)</span>
              <input
                type="number"
                step="0.1"
                value={payload.organic_matter}
                onChange={(event) => onChange('organic_matter', Number(event.target.value))}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                min="0"
                max="15"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Moisture (%)</span>
              <input
                type="number"
                step="0.5"
                value={payload.moisture}
                onChange={(event) => onChange('moisture', Number(event.target.value))}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                min="0"
                max="100"
              />
            </label>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Language</span>
              <select
                value={payload.lang}
                onChange={(event) => onChange('lang', event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
              >
                {languages.map((lang) => (
                  <option key={lang.value} value={lang.value}>{lang.label}</option>
                ))}
              </select>
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Latitude</span>
                <input
                  type="text"
                  value={payload.latitude}
                  onChange={(event) => onChange('latitude', event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Longitude</span>
                <input
                  type="text"
                  value={payload.longitude}
                  onChange={(event) => onChange('longitude', event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 focus:border-sky-500 focus:outline-none"
                />
              </label>
            </div>
          </div>

          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-2xl bg-sky-600 px-6 py-3 text-white transition hover:bg-sky-700"
          >
            {loading ? 'Assessing...' : 'Run Assessment'}
          </button>
        </form>

        {error && (
          <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {response && (
          <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-6">
            <h2 className="text-2xl font-semibold text-slate-900">Recommendation</h2>
            <p className="mt-3 text-slate-700">{response.recommendation}</p>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">Confidence</p>
                <p className="mt-2 text-3xl font-bold text-slate-900">{response.confidence ?? 'N/A'}</p>
              </div>
              <div className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">Triggered rules</p>
                <ul className="mt-2 space-y-2 text-sm text-slate-700">
                  {(response.triggered_rules || []).map((rule) => (
                    <li key={rule} className="rounded-xl bg-slate-100 px-3 py-2">{rule}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-4 shadow-sm">
              <p className="text-sm font-semibold text-slate-600">Explanation</p>
              <p className="mt-2 text-slate-700">{response.explanation}</p>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">SoilGrids</p>
                <pre className="mt-2 overflow-x-auto text-xs text-slate-700">{JSON.stringify(response.soilgrids, null, 2)}</pre>
              </div>
              <div className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">Weather</p>
                <pre className="mt-2 overflow-x-auto text-xs text-slate-700">{JSON.stringify(response.weather, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
