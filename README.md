# Mirpur Route Lab v3

Python Flask / Vercel interactive search-algorithm educational tool using **real OpenStreetMap geometry in Mirpur, Dhaka**. Congestion and road-risk values are **synthetic** and must not be treated as current traffic or safety information.

## Features

- Map: Leaflet + OpenStreetMap tiles, Overpass highway graph, named landmarks and click-to-select endpoints.
- 10 algorithms: BFS, DFS, DLS, IDS, UCS, bidirectional BFS on directed roads, Greedy Best-First, A*, Weighted A* and Beam Search.
- Road closure locations; traffic and safety risk multipliers; physical-distance-only and generalized-distance objectives.
- Map displays the route, sampled expanded nodes, the current expanded node and a bounded frontier snapshot; Play/Pause/Next and progress slider. Traces are capped to protect browser/server.
- Same-scenario 10-algorithm comparison: distances, costs, expansions, runtime and frontier peaks; CSV export.
- 100 and 500 node **induced subgraph** experiments on actual OSM nodes, with explicit No route if disconnected.
- API `/api/health`, `/api/graph`, `/api/route`, `/api/compare`, `/api/experiment`.

## Run on Ubuntu

```bash
cd mirpur-route-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python api/index.py
```

Open http://127.0.0.1:5000 . Your browser and server must have Internet access for OSM tiles and Overpass queries. If Overpass is down, graph fetch returns a clear 503; routes need a successfully fetched graph. The Flask server caches the graph in memory for one hour per warm instance; on Vercel, cold starts fetch it again.

## Deploy

Push to a GitHub repository connected to Vercel (Framework Preset: Flask; root `./`). `vercel.json` declares Flask framework. Deployments must be **runtime-tested** by visiting `/`, `/api/health` and `/api/graph`; a Vercel Ready build alone does not validate the Overpass network connection. No live API key is required.

## Assumptions and limitations

- OSM represents real road geometry and directionality where tagged. This model does **not** model turn restrictions, vehicle-specific rules, trip duration, speed, or real-time traffic.
- Objective `distance` uses road-edge length; `weighted` uses synthetic traffic and risk penalties, always at least the base distance. With this model Haversine is an admissible lower bound for A*, and UCS and A* return minimum-cost routes on the built directed graph when search completes.
- BFS/IDS/bidirectional BFS minimize **edge count** (not km). DFS, DLS, Greedy, Beam, and Weighted A* are not generally optimal. IDS repeats expansions. Limits can cause non-completion.
- Bidirectional BFS uses full forward/reverse traversals to obtain correct minimum-edge paths, favoring correctness over bidirectional early-exit performance.
- `runtime_ms` is one server-side invocation with no statistical repeats. Experiment subgraphs may be disconnected, which is reported without manufacturing values. The 100/500 experiments do not imply a controlled complexity law; compare qualitative trends only.
- Graph exploration displays at most 5,000 coordinates; frontier snapshots cover at most the first 2,500 expansion events, rendered with sampling for browser performance. `expanded` is the full expansion count; it can exceed shown dots.
- Synthetic risk is **not** actual personal safety; app is not suitable for navigation or emergency response.

## GitHub update from old version

Download the upgraded ZIP, **back up any local edits**, extract and copy the upgraded project files into your existing repository folder. Keep your existing `.git` directory. Then:

```bash
git add .
git commit -m "Upgrade Mirpur Route Lab algorithms and experiments"
git push origin main
```

## Test

`python -m unittest discover -s tests -v` for graph-level regression checks; production OSM/Overpass integration still requires internet testing.


## Emergency dispatch scenario controls (v4)
Incident: rescue, medical emergency, fire response, snatching, robbery, theft. Independent departure/destination landmark dropdowns or map clicks. Traffic: 0.15 / 0.45 / 0.85. Benchmark node count: 10–1500 (and reference 100/500 graphs). Time: morning/midday/evening/night. Weather: summer/monsoon/winter. Priority: balanced/fastest/avoid congestion. Vehicles: ambulance/fire engine/rescue van/police patrol.

All dispatch effects are deterministic educational *simulation*, not observed traffic, official emergency service speeds, verified road access or public safety information. Road geometry is requested from OpenStreetMap. Mode **Distance** deliberately ignores dispatch penalties; use **Weighted** to make scenario settings affect optimization. ETA is a modeled estimate, not travel advice. Benchmark graphs may be disconnected.

## Dynamic benchmark graphs (v5)

After opening the existing app, scroll below the comparison tables to **Search and safety graphs**. Choose an objective (composite, distance, time, safety), set graph node count and emergency conditions, and click **Update all graphs**. The UI renders seven interactive bar-chart sections: node expansions (log scale), distance, estimated travel time, composite path score, safety score, risk exposure, and measured runtime. Each algorithm has Low/Medium/High simulated traffic bars. No prefabricated data or PNG chart is used.

The endpoint `POST /api/benchmark-graphs` measures 10 algorithms × 3 traffic scenarios on a deterministic connected sampled subgraph of real OSM road nodes. Graph counts represent sample sizes, not road-network-size modifications. The source/destination benchmark pair is chosen reproducibly from the sampled graph (the start is snapped to a road). Traffic/risk and safety are **synthetic**; road geometry comes from OpenStreetMap. `composite` graph score is defined as `ETA(minutes) + 4 × risk_weight × simulated_exposure`; `safety` graph score is `distance(km) + risk_weight × simulated_exposure`. These are interpretation scores for each returned path, not guaranteed globally optimal objectives; optimization uses the selected benchmark objective. Runtime values represent a single unaveraged request execution. Paths that cannot be found under algorithm depth constraints are marked N/A. Large node selections can take significantly longer.

This ZIP is an **overlay of the existing `mirpur-route-lab` repo**, not a replacement repository. It cannot automatically push to GitHub or change your Vercel deployment until you run `git push origin main` in your existing checkout.


### v6: All ten algorithm dynamic charts
The same seven chart domains now include BFS, DFS, DLS, IDS, UCS, Bidirectional BFS, Greedy Best-First, A*, Weighted A*, and Beam Search under all three synthetic traffic levels (30 benchmark runs). DLS/IDS/Beam can return N/A for limited depths or beam widths; that is a valid and visible outcome, not a fabricated route. The benchmark honors the sidebar depth, beam-width, and heuristic-weight inputs (depth is capped at 12 for the benchmark to limit serverless work). For large graphs, execution can still be slow; use smaller samples.

## Two-mode dashboard (v7)
Choose **Route Simulation** for the original ten algorithms and dynamic traffic/cost graphs, or **Emergency Response** for a separate educational dispatch allocation view.
Emergency Response offers 100/150/250 synthetic incidents, ambulance/rescue/fire units, capability and remaining-capacity constraints, simulated blocked zones, configurable 120-minute default deadline, summary statistics, a map, detailed request allocation, and comparisons between bounded heuristic CSP-inspired strategies.
**Limitation:** emergency assignments use Haversine estimates and synthetic detour multipliers, not actual OSM shortest-path travel times; no unit is dispatched in reality. The CSP-like heuristics are not proof of global optimum, and traffic/safety are simulated. Emergency map markers indicate modelled locations only.

## Fix: Overpass 'read operation timed out' on Vercel

Vercel functions do not share a persistent Python memory cache. Querying Mirpur's entire road network from Overpass during an HTTP request is unreliable. **For production, bundle an actual OSM road snapshot** and let the Flask API load it immediately without calling Overpass. The application never fabricates road geometry.

On Ubuntu in this existing Git repository, run:

```bash
python3 scripts/cache_mirpur_roads.py
```

This standard-library-only script downloads four small pieces of the original Mirpur bounding box, merges the real OpenStreetMap ways, and writes `data/mirpur_roads.json.gz`. If a mirror times out it tries another; if all fail, try again later. You can also provide a saved Overpass JSON response with `--from-json path/to/overpass.json`.

Then commit and redeploy to **the same existing Vercel project**:

```bash
git add api/index.py scripts/cache_mirpur_roads.py data/mirpur_roads.json.gz tests/test_snapshot.py README.md
git commit -m "Bundle Mirpur road graph to prevent Overpass timeouts"
git push origin main
```

Before uploading the snapshot, `GET /api/health` should return `"snapshot_available": true` locally. After Vercel redeploys, the same endpoint confirms the snapshot was bundled. Live map tiles are independent of the road graph; seeing the base map does not imply route graph availability. The bundled snapshot is a fixed OSM data extract and is not live traffic information. To update the geometry later, rerun with `--force` and commit the new snapshot.


## A* Heuristic Inspector

The route explorer includes a synchronized heuristic inspector for A*, Weighted A*, and Greedy Best-First Search. Moving the expansion slider or using Play / Next Step updates the selected node's recorded `g(n)`, Haversine `h(n)`, queue priority `f(n)`, coordinates, and recent expansion history.

- A*: `f(n) = g(n) + h(n)`
- Weighted A*: `f(n) = g(n) + w × h(n)`
- Greedy Best-First: queue priority is `h(n)` (the trace also reports accumulated `g(n)` for context).

Important unit note: `h(n)` is Haversine distance in kilometres. `g(n)` is accumulated edge cost in the selected objective's units. Those units may differ in time, safety, weighted, or composite modes. The inspector displays the values actually used by the implementation; it does not claim the heuristic is admissible for every objective.
