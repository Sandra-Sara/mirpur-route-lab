# A* Heuristic Inspector

Implemented in the existing route explorer without replacing the map, search controls, emergency response mode, or benchmark graphs.

## What is recorded
For A*, Weighted A*, and Greedy Best-First, each expanded node trace records:
- `g`: accumulated objective edge cost to the node
- `h`: straight-line Haversine distance from the node to the goal (km)
- `f`: actual popped queue priority
- formula name and Weighted A* weight (where applicable)

The API maps node IDs to coordinates and includes these values in `trace_coordinates`. The existing expansion progress slider, Play, and Next Step controls drive the inspector.

## Formulas
- A*: `g(n) + h(n)`
- Weighted A*: `g(n) + w × h(n)`
- Greedy Best-First: `h(n)` priority; `g(n)` remains visible as path-cost context.

## Unit / optimality caveat
The Haversine heuristic is in kilometres. Accumulated `g(n)` uses the selected edge-cost objective. In non-distance objectives, units may differ. Therefore, the UI explicitly warns that the recorded values do not imply A* optimality for every configured objective.
