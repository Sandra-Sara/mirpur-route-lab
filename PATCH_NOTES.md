# Mirpur Route Lab — timeout resilience patch

This patch changes only api/index.py and static/index.html plus these notes.

- Existing bundled real OSM road snapshot is preferred.
- A live Overpass query is tried with short timeouts when the snapshot is absent.
- If both providers fail, the app generates a connected 32x32 synthetic coordinate grid within the Mirpur study bounding box, so algorithm demonstrations, comparisons and graphs still operate.
- Simulated grid links are NOT real streets. The UI and responses identify simulated mode explicitly; routes are unsuitable for actual navigation or emergency response.
- Emergency Response CSP simulation is unchanged.
- To restore *actual* roads without flaky Overpass calls, a genuine OSM road snapshot remains necessary. The fallback must not be passed off as real data.

To update the existing GitHub repository:
  cd ~/Downloads
  unzip -o mirpur-existing-app-timeout-patch.zip
  cd mirpur-route-lab
  python3 -m unittest discover -s tests -v
  git add api/index.py static/index.html PATCH_NOTES.md
  git commit -m "Keep existing app working when Overpass times out"
  git push origin main

Check the road source in the application's top status badge and Algorithm insight > Graph. It should say SIMULATED GRAPH if OSM was unavailable.
