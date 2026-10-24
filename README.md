# Mirpur Route Lab

A Python Flask + Leaflet web application for graph search over real OpenStreetMap streets of Mirpur, Dhaka, prepared for Vercel deployment.

### Features
- Actual OSM street geometry from Overpass, with serverless memory cache.
- Start/destination map selection and Mirpur landmark presets.
- BFS, DFS, DLS, IDS, UCS, Greedy Best-First, A*, Weighted A*, Beam Search, Bidirectional BFS.
- Adjustable multi-criteria synthetic congestion and safety costs; simulated blocked intersections.
- Haversine heuristic, real distance in km, search expansion counts, route visualization and exploration scrubber.
- Mobile-friendly modern dashboard and project REPORT.md.

### Local installation
```bash
pip install -r requirements.txt
python api/index.py
```
Then open http://localhost:5000

### Deploy to Vercel
1. Unzip this project, commit its contents to a GitHub repository.
2. Import the repository at https://vercel.com/new .
3. Choose Flask/Python framework detection and deploy. `vercel.json` configures `api/index.py`.
4. Open the deployed URL. Internet connectivity and public Overpass uptime are necessary for routing.

No external API key is required for demo use. Public Overpass APIs are best-effort; serious production usage should pre-generate and host an OSM street graph rather than call Overpass on user requests.

See `REPORT.md` for the mathematical model, assumptions, complexity, limitations, and experiment suggestions.
