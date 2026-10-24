# Mirpur Route Lab — Search Algorithms Project Report

## 1. Problem statement and objective

This project models street routing in Mirpur, Dhaka as a directed, weighted graph. Each intersection / sampled road node is a vertex; road segments are edges. The user selects two map coordinates, which are snapped to their nearest road nodes. The solver compares different graph search algorithms and displays the selected route and explored nodes. The objective can emphasize distance alone or a generalized cost combining distance, simulated traffic congestion, and simulated safety risks.

## 2. Data and assumptions

- Base map: OpenStreetMap raster tiles (attribution displayed).
- Routing network: live OpenStreetMap highway ways obtained through the Overpass API and cached in the serverless worker for up to one hour.
- Region: bounding box latitude 23.778–23.840 and longitude 90.335–90.405, covering Mirpur and adjacent areas.
- Bidirectional roads are modeled with two directed edges; streets tagged as one-way are modeled with a single directed edge. Some road restrictions (turn restrictions, traffic lights, vehicle restrictions, temporal rules) are not modeled.
- Edge length is calculated using the Haversine geodesic formula; this approximates each small road segment's geographic length.
- Congestion and safety parameters are **synthetic**, deterministic coefficients derived from road class and an edge identifier. These are not actual traffic measurements, live congestion, crime reports, or verified danger zones. They are appropriate for a course simulation, not real-world safety advice.
- Blocking a map point disables outgoing and incoming links at the nearest road vertex, creating a simulated road closure. The graph is not altered permanently.

## 3. Mathematical model

For road edge (u, v), let d(u,v) be its distance in kilometers, t(u,v) a simulated congestion factor, and s(u,v) a simulated safety-risk factor. With traffic weight α and safety weight β:

`c(u,v) = d(u,v) × [1 + α t(u,v) + β s(u,v)]`

The two supported objectives are: distance-only `g = Σ d` and multi-criteria generalized cost `g = Σ c`. The returned **generalized cost** is reported even if a distance-only objective was used; it is a synthetic distance-equivalent score, not minutes or money. For A* and its variants:

`h(n) = HaversineDistance(n, goal)`

`f(n) = g(n) + h(n)` (A*)

`f(n) = g(n) + w h(n)` (Weighted A*)

Because each computed generalized edge cost is at least its geographic length, the straight-line distance is an admissible lower bound for the generalized cost objective as well as for the distance-only objective. It is also consistent under nonnegative penalties and standard edge distances.

## 4. Search methods

| Algorithm | Frontier decision | Cost optimal? | Key remark |
|---|---|---|---|
| BFS | FIFO | No, except for equal edge costs | Fewest edges |
| DFS | LIFO | No | Can explore very long branches |
| DLS | LIFO, depth cutoff | No | May fail if depth too low |
| IDS | Increasing DLS cutoffs | No for weighted road networks | Repeat expansions |
| UCS | Lowest g | Yes for nonnegative edges | Dijkstra-style |
| Greedy Best First | Lowest h | No | Quick estimate, may be suboptimal |
| A* | Lowest g + h | Yes with consistent admissible h | Recommended balanced solver |
| Weighted A* | Lowest g + wh | Not necessarily | Can trade quality for search effort |
| Beam | Retain top-k h per layer | No | Memory-limited approximation |
| Bidirectional BFS | FIFO from both directions | No for weighted edges | Reversed graph handles one-way roads |

This application counts graph expansions. The map displays up to 4,000 expanded coordinates and samples rendered points to maintain interactivity. Larger searches can stop at expansion caps to stay within serverless execution limits. Algorithms operate on the road-node graph, so a short physical road with many intermediate nodes may be disadvantaged by BFS even if physically shorter.

## 5. Implementation and user interaction

Frontend: responsive HTML/CSS/JavaScript with Leaflet, OSM tiles, algorithm selector, road selection, synthetic traffic/safety sliders, road-block markers, route map, result metrics, and an exploration-progress slider. Backend: Python Flask JSON endpoints. Vercel supports deployment of Python functions from `api/index.py` with the included `vercel.json`.

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python api/index.py
```

Open `http://localhost:5000` in a browser. Requires internet access to download Leaflet and map tiles and fetch Overpass road geometry. For Vercel: import the code repository in Vercel, or use `vercel` from the project folder after authenticating. The Overpass service may rate-limit or time out; the app visibly reports these errors and does not silently substitute fake roads.

## 6. Suggested experiments

Use the same source and destination for all algorithms. Record algorithm, physical route length, generalized route cost, number of nodes expanded, and graph steps. Repeat under three synthetic traffic levels (0, 0.6, 2) and different safety weights. Introduce a blocked intersection and see if alternative routes remain. Compare A* vs UCS to check optimal cost (with the same objective), BFS vs UCS to distinguish fewest hops from least cost, and Weighted A* vs A* to observe the exploration/cost trade-off.

## 7. Limitations and future extensions

For an extended project, add live traffic with a properly licensed provider, actual accident/safety statistics, travel times/speed limits, restrictions and turn penalties, road segment blocking, graph connectivity checks, A* time/memory benchmarks, and optionally improved algorithms such as IDA*, RBFS, and SMA*. A persistent preprocessed graph database would reduce Overpass dependence and cold-start latency. Avoid claiming synthetic risk and congestion are verified on-the-ground conditions.
