import json, math, os, heapq, time, urllib.request, urllib.parse
from collections import deque
from flask import Flask, request, jsonify, send_from_directory

app=Flask(__name__,static_folder='../static')
ROOT=os.path.dirname(os.path.dirname(__file__))
BBOX=(23.778,90.335,23.840,90.405)
_CACHE={'when':0,'data':None}

@app.get('/')
def home():return send_from_directory(os.path.join(ROOT,'static'),'index.html')

def distance(a,b):
    lat1,lon1=a;lat2,lon2=b;r=6371.0
    p1,p2=math.radians(lat1),math.radians(lat2)
    v=math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 2*r*math.asin(min(1,math.sqrt(v)))

def fetch_roads():
    if _CACHE['data'] and time.time()-_CACHE['when']<3600:return _CACHE['data']
    s,w,n,e=BBOX
    q=f'''[out:json][timeout:24];(way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|living_street|service|primary_link|secondary_link|tertiary_link)$"]({s},{w},{n},{e}););out geom;'''
    errors=[]
    for host in ['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter','https://overpass.nchc.org.tw/api/interpreter']:
        try:
            payload=urllib.parse.urlencode({'data':q}).encode()
            req=urllib.request.Request(host,data=payload,headers={'User-Agent':'MirpurRouteLab/1.0 (educational mapping application)','Content-Type':'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req,timeout=29) as resp: raw=json.load(resp)
            nodes={}; edges={}; ways=[]
            for way in raw.get('elements',[]):
                if way.get('type')!='way' or len(way.get('geometry',[]))<2:continue
                ids=way['nodes'];geo=way['geometry']; tags=way.get('tags',{}); kind=tags.get('highway','residential');oneway=tags.get('oneway') in ('yes','1','true') or tags.get('junction')=='roundabout'
                if tags.get('oneway')=='-1': ids=list(reversed(ids));geo=list(reversed(geo));oneway=True
                for nid,point in zip(ids,geo):nodes[str(nid)]=[point['lat'],point['lon']]
                ways.append({'ids':[str(x) for x in ids],'kind':kind,'name':tags.get('name','Unnamed road'),'oneway':oneway})
            for way in ways:
                ids=way['ids']
                for a,b in zip(ids,ids[1:]):
                    if a==b:continue
                    d=distance(nodes[a],nodes[b]);
                    if d==0:continue
                    edges.setdefault(a,[]).append([b,round(d,6),way['kind'],way['name']])
                    if not way['oneway']:edges.setdefault(b,[]).append([a,round(d,6),way['kind'],way['name']])
            graph={'nodes':nodes,'edges':edges,'ways':len(ways),'source':'OpenStreetMap / Overpass API','updated':int(time.time())}
            if len(nodes)<100:raise RuntimeError('Road network response too small')
            _CACHE.update({'when':time.time(),'data':graph});return graph
        except Exception as ex:errors.append(str(ex)[:120])
    raise RuntimeError('OpenStreetMap road data could not be loaded. Please retry. '+'; '.join(errors[:1]))

@app.get('/api/graph')
def graph():
    try:
        g=fetch_roads();return jsonify({'nodes':g['nodes'],'edgeCount':sum(map(len,g['edges'].values())),'ways':g['ways'],'source':g['source'],'updated':g['updated']})
    except Exception as ex:return jsonify({'error':str(ex)}),503

from api.search import route_search, haversine

@app.post('/api/route')
def route():
    try:
        p=request.get_json(force=True);g=fetch_roads();nodes=g['nodes']
        def nearest(pos):return min(nodes,key=lambda k:distance(pos,nodes[k]))
        start=nearest(p['start']);end=nearest(p['end']);blocks=[]
        for item in p.get('blocks',[])[:30]:
            near=nearest(item);blocks.extend(frozenset((near,v)) for v,*_ in g['edges'].get(near,[]))
        result=route_search(g,start,end,p.get('algorithm','astar'),p.get('mode','weighted'),min(3,max(0,float(p.get('traffic',0.6)))),min(3,max(0,float(p.get('risk',0.5)))),set(blocks),min(5,max(1,float(p.get('weight',1.5)))),min(500,max(1,int(p.get('depth',60)))),min(300,max(1,int(p.get('beam',25)))))
        result['coordinates']=[nodes[x] for x in result.get('path',[])];result['explored_coordinates']=[nodes[x] for x in result.get('explored',[])];result['snapped_start']=nodes[start];result['snapped_end']=nodes[end];result['graph_nodes']=len(nodes);return jsonify(result)
    except Exception as ex:return jsonify({'error':str(ex)}),400

@app.get('/api/health')
def health():return jsonify({'ok':True,'region':'Mirpur, Dhaka','graph_cached':bool(_CACHE['data'])})

if __name__=='__main__':app.run(debug=True,port=5000)

@app.post('/api/compare')
def compare():
    try:
        p=request.get_json(force=True);g=fetch_roads();nodes=g['nodes']
        nearest=lambda xy:min(nodes,key=lambda k:distance(xy,nodes[k]))
        start=nearest(p['start']);goal=nearest(p['end']);blocked=set()
        for item in p.get('blocks',[])[:30]:
            u=nearest(item);blocked.update(frozenset((u,v)) for v,*_ in g['edges'].get(u,[]))
        opts={'mode':p.get('mode','weighted'),'traffic':min(3,max(0,float(p.get('traffic',.6)))),'risk':min(3,max(0,float(p.get('risk',.5)))),'blocked':blocked,'depth':min(500,max(1,int(p.get('depth',60)))),'beam':min(300,max(1,int(p.get('beam',25)))),'weight':min(5,max(1,float(p.get('weight',1.5))))}
        rows=[]
        for alg in ('bfs','dfs','dls','ids','ucs','bidirectional','greedy','astar','weighted','beam'):
            r=route_search(g,start,goal,algorithm=alg,**opts)
            rows.append({k:r[k] for k in ('algorithm','expanded','distance','cost','runtime_ms','frontier_peak','steps','optimality')})
        return jsonify({'results':rows,'graph_nodes':len(nodes),'start':nodes[start],'end':nodes[goal]})
    except Exception as ex:return jsonify({'error':str(ex)}),400

@app.post('/api/experiment')
def experiment():
    try:
        p=request.get_json(force=True);g=fetch_roads();nodes=g['nodes'];nearest=lambda xy:min(nodes,key=lambda k:distance(xy,nodes[k]))
        start=nearest(p['start']);goal=nearest(p['end']);rows=[]
        # Reproducible induced subgraphs around endpoints using a deterministic spatial ranking.
        for size in (100,500):
            scored=sorted(nodes,key=lambda u:(distance(nodes[u],nodes[start])+distance(nodes[u],nodes[goal]),str(u)))
            allowed=set(scored[:size])|{start,goal}
            for alg in ('bfs','ucs','astar','greedy'):
                r=route_search(g,start,goal,algorithm=alg,mode=p.get('mode','weighted'),traffic=float(p.get('traffic',.6)),risk=float(p.get('risk',.5)),allowed=allowed)
                rows.append({'graph_size':len(allowed),'algorithm':alg,'distance':r['distance'],'cost':r['cost'],'expanded':r['expanded'],'runtime_ms':r['runtime_ms']})
        return jsonify({'results':rows,'method':'Deterministic top-N geographic induced subgraph containing both selected endpoints. Disconnection is possible; null cost means no route. Timings are server runtime per run, not benchmark averages.','graph_nodes':len(nodes)})
    except Exception as ex:return jsonify({'error':str(ex)}),400
