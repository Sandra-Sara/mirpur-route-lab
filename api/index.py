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

def route_search(g,start,goal,alg,mode,traffic,risk,blocked,weight,depth,beam):
    nodes=g['nodes'];edges=g['edges']
    if start not in nodes or goal not in nodes:raise ValueError('Please choose valid road points')
    if start==goal:return {'path':[start],'explored':[start],'expanded':1,'cost':0,'distance':0,'risk':0,'algorithm':alg}
    # Distances always in km; cost is generalized distance equivalent (km).
    def h(u):return distance(nodes[u],nodes[goal])
    def edge_cost(u,v,d,kind):
        corridor=(sum((i+1)*ord(ch) for i,ch in enumerate(min(u,v)+max(u,v)))%1000)/1000
        congestion=(0.65 if kind in ('primary','secondary','trunk') else 0.25)+0.35*corridor
        safety=(0.25 if kind in ('primary','secondary') else 0.55)+0.4*corridor
        return d*(1+traffic*congestion+risk*safety),safety*d
    def neighbors(u):
        for v,d,kind,name in edges.get(u,[]):
            if frozenset((u,v)) in blocked:continue
            c,r=edge_cost(u,v,d,kind)
            yield v,d,c,r
    expanded=[];parents={start:None};costs={start:0};counts=0
    if alg in ('bfs','dfs','dls','ids'):
        def dfs_limit(limit):
            stack=[(start,0)]; local={start:None};bestdepth={start:0};seen=[]
            while stack and len(seen)<25000:
                u,dep=stack.pop();seen.append(u)
                if u==goal:return local,seen
                if dep>=limit:continue
                seq=list(neighbors(u))
                if alg!='bfs':seq.reverse()
                for v,*_ in seq:
                    if v not in bestdepth or dep+1<bestdepth[v]:
                        bestdepth[v]=dep+1;local[v]=u;stack.append((v,dep+1))
            return None,seen
        if alg=='bfs':
            q=deque([start]);seen={start}
            while q and len(expanded)<25000:
                u=q.popleft();expanded.append(u)
                if u==goal:break
                for v,*_ in neighbors(u):
                    if v not in seen:seen.add(v);parents[v]=u;q.append(v)
        elif alg=='ids':
            for lim in range(0,min(depth,100)+1):
                p,ex=dfs_limit(lim);expanded+=ex
                if p is not None:parents=p;break
                if len(expanded)>40000:break
        else:
            p,expanded=dfs_limit(depth if alg=='dls' else 15000)
            if p is not None:parents=p
    elif alg=='bidirectional':
        # Directed OSM streets: reverse graph for backward frontier
        rev={}
        for u,arr in edges.items():
            for v,d,k,name in arr:
                if frozenset((u,v)) not in blocked:rev.setdefault(v,[]).append(u)
        front=deque([start]);back=deque([goal]);pa={start:None};pb={goal:None};meet=None
        while front and back and len(expanded)<25000:
            forward=len(front)<=len(back)
            q,own,other=(front,pa,pb) if forward else (back,pb,pa)
            for _ in range(len(q)):
                u=q.popleft();expanded.append(u)
                if u in other:meet=u;break
                nxt=(v for v,*_ in neighbors(u)) if forward else iter(rev.get(u,[]))
                for v in nxt:
                    if v not in own:own[v]=u;q.append(v)
                    if v in other:meet=v;break
                if meet is not None:break
            if meet is not None:break
        if meet is not None:
            path=[];u=meet
            while u is not None:path.append(u);u=pa[u]
            path.reverse();u=pb[meet]
            while u is not None:path.append(u);u=pb[u]
            parents={path[0]:None}
            for u,v in zip(path,path[1:]):parents[v]=u
    elif alg=='beam':
        layer=[start];visited={start}
        for _ in range(max(1,depth)):
            if not layer or goal in layer:break
            expanded+=layer
            nxt=[]
            for u in layer:
                for v,d,c,r in neighbors(u):
                    if v not in visited:visited.add(v);parents[v]=u;nxt.append(v)
            layer=sorted(nxt,key=h)[:beam]
        expanded+=layer
    else:
        pq=[];seq=0;heapq.heappush(pq,(0,seq,start));closed=set()
        while pq and len(expanded)<35000:
            _,_,u=heapq.heappop(pq)
            if u in closed:continue
            closed.add(u);expanded.append(u)
            if u==goal:break
            for v,d,c,r in neighbors(u):
                if v in closed:continue
                step=1 if alg=='greedy' else (d if mode=='distance' else c)
                new=costs[u]+step
                if new<costs.get(v,float('inf')):
                    costs[v]=new;parents[v]=u;seq+=1
                    priority={'ucs':new,'astar':new+h(v),'weighted':new+weight*h(v),'greedy':h(v)}.get(alg,new+h(v))
                    heapq.heappush(pq,(priority,seq,v))
    if goal not in parents:return {'path':[],'explored':expanded[:4000],'expanded':len(expanded),'message':'No route found. Try another algorithm, increase depth/beam width, or remove blocks.','algorithm':alg}
    path=[];u=goal
    while u is not None and len(path)<len(nodes)+2:
        path.append(u);u=parents.get(u)
    path.reverse()
    if path[0]!=start:return {'path':[],'explored':expanded[:4000],'expanded':len(expanded),'message':'Path reconstruction failed'}
    dist=total=risk_total=0
    detail=[]
    for u,v in zip(path,path[1:]):
        match=next((x for x in edges[u] if x[0]==v),None)
        if match is None:continue
        _,d,k,name=match;c,r=edge_cost(u,v,d,k);dist+=d;total+=c;risk_total+=r
        detail.append({'name':name,'km':round(d,4),'cost':round(c,4)})
    return {'path':path,'explored':expanded[:4000],'expanded':len(expanded),'distance':round(dist,3),'cost':round(total,3),'risk':round(risk_total,3),'algorithm':alg,'steps':len(path)-1,'segments':detail,'mode':mode}

@app.post('/api/route')
def route():
    try:
        p=request.get_json(force=True);g=fetch_roads();nodes=g['nodes']
        def nearest(pos):return min(nodes,key=lambda k:distance(pos,nodes[k]))
        start=nearest(p['start']);end=nearest(p['end']);blocks=[]
        for item in p.get('blocks',[])[:30]:
            near=nearest(item);blocks.extend(frozenset((near,v)) for v,*_ in g['edges'].get(near,[]))
        result=route_search(g,start,end,p.get('algorithm','astar'),p.get('mode','weighted'),min(3,max(0,float(p.get('traffic',0.6)))),min(3,max(0,float(p.get('risk',0.5)))),set(blocks),min(5,max(1,float(p.get('weight',1.5)))),min(100,max(1,int(p.get('depth',60)))),min(300,max(1,int(p.get('beam',25)))))
        result['coordinates']=[nodes[x] for x in result.get('path',[])];result['explored_coordinates']=[nodes[x] for x in result.get('explored',[])];result['snapped_start']=nodes[start];result['snapped_end']=nodes[end];result['graph_nodes']=len(nodes);return jsonify(result)
    except Exception as ex:return jsonify({'error':str(ex)}),400

@app.get('/api/health')
def health():return jsonify({'ok':True,'region':'Mirpur, Dhaka','graph_cached':bool(_CACHE['data'])})

if __name__=='__main__':app.run(debug=True,port=5000)
