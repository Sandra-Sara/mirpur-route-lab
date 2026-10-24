"""Deterministic directed road-graph search algorithms (educational simulation)."""
from collections import deque
import heapq, math, time

LIMIT=50000

def haversine(a,b):
    lat1,lon1=map(math.radians,a);lat2,lon2=map(math.radians,b)
    x=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742*math.asin(min(1,math.sqrt(x)))

def route_search(graph,start,goal,algorithm='astar',mode='weighted',traffic=.6,risk=.5,blocked=None,weight=1.5,depth=60,beam=25,allowed=None,incident='rescue',time_of_day='midday',weather='winter',priority='balanced',vehicle='ambulance'):
    t0=time.perf_counter();nodes=graph['nodes'];edges=graph['edges'];blocked=blocked or set()
    if start not in nodes or goal not in nodes:raise ValueError('Invalid selected nodes')
    if algorithm not in {'bfs','dfs','dls','ids','ucs','bidirectional','greedy','astar','weighted','beam'}:raise ValueError('Unknown algorithm')
    if mode not in {'distance','weighted'}:raise ValueError('Unknown objective')
    allowed=set(nodes) if allowed is None else set(allowed)
    if start not in allowed or goal not in allowed:raise ValueError('Endpoints outside experiment subgraph')
    depth=max(0,int(depth));beam=max(1,int(beam));weight=max(1,float(weight))
    def heuristic(u):return haversine(nodes[u],nodes[goal])
    def risk_level(u,v,kind):
        seed=sum((i+1)*ord(ch) for i,ch in enumerate('|'.join(sorted((str(u),str(v))))) )%997/997
        return (0.25 if kind in ('primary','secondary','trunk') else .55)+.40*seed
    INCIDENTS={'rescue','medical','fire','snatching','robbery','theft'}
    TIMES={'morning':1.20,'midday':1.0,'evening':1.45,'night':0.70}
    WEATHER={'summer':1.0,'monsoon':1.40,'winter':1.13}
    VEHICLES={'ambulance':1.0,'fire_engine':0.76,'rescue_van':0.90,'police_patrol':1.10}
    PRIORITIES={'balanced','fastest','avoid_congestion'}
    if incident not in INCIDENTS or time_of_day not in TIMES or weather not in WEATHER or priority not in PRIORITIES or vehicle not in VEHICLES:
        raise ValueError('Invalid emergency dispatch scenario')
    arterial={'motorway','trunk','primary','secondary','tertiary','primary_link','secondary_link','tertiary_link'}
    def conditions(u,v,kind):
        q=risk_level(u,v,kind)
        road_congestion=(.65 if kind in arterial else .25)+.35*(q%1)
        congestion=min(2.5,max(0,float(traffic))*TIMES[time_of_day]*WEATHER[weather]*road_congestion)
        speed=(42 if kind in arterial else 23)*VEHICLES[vehicle]
        if vehicle=='fire_engine' and kind in {'living_street','service'}:speed*=.65
        # All quantities are deterministic scenario estimates, not live observations.
        minutes=60/(max(5,speed))*(1+congestion)
        return q,congestion,minutes
    def cost(u,v,d,kind):
        q,c,minutes_per_km=conditions(u,v,kind)
        if mode=='distance':return d
        if priority=='fastest':return d*(1+minutes_per_km/2)
        if priority=='avoid_congestion':return d*(1+2.2*c+.3*risk*q)
        incident_risk={'rescue':.8,'medical':.65,'fire':1.0,'snatching':1.2,'robbery':1.5,'theft':1.1}[incident]
        return d*(1+0.8*c+risk*q*incident_risk+minutes_per_km/8)

    def neighbor(u):
        for v,d,k,name in edges.get(u,[]):
            if v in allowed and frozenset((u,v)) not in blocked:
                yield v,d,k,name,cost(u,v,d,k)
    explored=[]; parents={start:None};found=False;frontier_peak=1; trace=[]
    def record(u, frontier):
        if len(trace)<2500:trace.append({'node':u,'frontier':list(frontier)[:120]})
    def capped():return len(explored)>=LIMIT
    if start==goal:found=True;explored.append(start)
    elif algorithm=='bfs':
        q=deque([start]);seen={start}
        while q and not capped():
            frontier_peak=max(frontier_peak,len(q));u=q.popleft();explored.append(u);record(u,q)
            if u==goal:found=True;break
            for v,*_ in neighbor(u):
                if v not in seen:seen.add(v);parents[v]=u;q.append(v)
    elif algorithm in ('dfs','dls','ids'):
        def visit(limit):
            # Tree-search with path-local cycle checking: does not discard a
            # shallower alternate path based on an earlier deep encounter.
            stack=[(start,(start,))];expanded=[];peak=1;steps=[]
            while stack and len(expanded)<LIMIT:
                peak=max(peak,len(stack));u,path=stack.pop();expanded.append(u)
                if len(steps)<2500:steps.append({'node':u,'frontier':[x[0] for x in stack[-120:]]})
                if u==goal:return path,expanded,peak,steps
                if len(path)-1>=limit:continue
                for v,*_ in reversed(list(neighbor(u))):
                    if v not in path:stack.append((v,path+(v,)))
            return None,expanded,peak,steps
        if algorithm=='ids':
            for limit in range(depth+1):
                p,e,pk,ts=visit(limit);explored.extend(e);trace.extend(ts[:max(0,2500-len(trace))]);frontier_peak=max(frontier_peak,pk)
                if p:found=True;break
                if capped():break
        else:
            p,explored,frontier_peak,trace=visit(len(allowed)-1 if algorithm=='dfs' else depth)
            found=bool(p)
        if found:
            parents={p[0]:None}
            for a,b in zip(p,p[1:]):parents[b]=a
    elif algorithm=='bidirectional':
        # Reverse BFS distances guarantee a minimum-edge path in a directed
        # network, including streets with one-way movement.
        reverse={}
        for u in allowed:
            for v,*_ in neighbor(u):reverse.setdefault(v,[]).append(u)
        qa=deque([start]);qb=deque([goal]);pa={start:None};pb={goal:None}
        # Fully discover reachable levels on both sides; reconstruct via the
        # meeting vertex minimizing dist(start,m)+dist(m,goal).
        da={start:0};db={goal:0}
        for q,own,dist,adj in ((qa,pa,da,lambda u:(v for v,*_ in neighbor(u))),
                                (qb,pb,db,lambda u:iter(reverse.get(u,[])))):
            while q and not capped():
                frontier_peak=max(frontier_peak,len(q));u=q.popleft();explored.append(u);record(u,q)
                for v in adj(u):
                    if v not in dist:
                        dist[v]=dist[u]+1;own[v]=u;q.append(v)
        meets=da.keys() & db.keys()
        if meets:
            meet=min(meets,key=lambda u:(da[u]+db[u],str(u)))
            p=[];u=meet
            while u is not None:p.append(u);u=pa[u]
            p.reverse();u=pb[meet]
            while u is not None:p.append(u);u=pb[u]
            parents={p[0]:None}
            for a,b in zip(p,p[1:]):parents[b]=a
            found=True
    elif algorithm=='beam':
        layer=[(start,(start,))]
        for _ in range(depth+1):
            if not layer or capped():break
            frontier_peak=max(frontier_peak,len(layer));nxt=[]
            for u,path in layer:
                explored.append(u);record(u,(x[0] for x in layer))
                if u==goal:p=path;found=True;break
                if capped():break
                for v,*_ in neighbor(u):
                    if v not in path:nxt.append((heuristic(v),v,path+(v,)))
            if found:break
            # keep one candidate per ending node at each depth
            seen=set();layer=[]
            for _,v,path in sorted(nxt,key=lambda x:(x[0],str(x[1]))):
                if v not in seen:seen.add(v);layer.append((v,path))
                if len(layer)>=beam:break
        if found:
            parents={p[0]:None}
            for a,b in zip(p,p[1:]):parents[b]=a
    else:
        pq=[];serial=0;gscore={start:0};heapq.heappush(pq,(heuristic(start) if algorithm in ('astar','greedy') else weight*heuristic(start) if algorithm=='weighted' else 0,0,start));closed=set()
        while pq and not capped():
            frontier_peak=max(frontier_peak,len(pq));popped_priority,_,u=heapq.heappop(pq)
            if u in closed:continue
            closed.add(u);explored.append(u);record(u,(item[2] for item in pq))
            if u==goal:found=True;break
            for v,d,k,name,c in neighbor(u):
                if algorithm=='greedy':
                    if v in closed or v in parents:continue
                    parents[v]=u;gscore[v]=gscore[u]+c;key=heuristic(v)
                else:
                    new=gscore[u]+c
                    if new>=gscore.get(v,math.inf)-1e-12:continue
                    gscore[v]=new;parents[v]=u
                    # Reopen improved nodes; admissible h <= edge cost because costs >= physical distance.
                    closed.discard(v)
                    key=new+(weight if algorithm=='weighted' else 1)*heuristic(v) if algorithm in ('astar','weighted') else new
                serial+=1;heapq.heappush(pq,(key,serial,v))
    path=[]
    if found:
        u=goal
        while u is not None and len(path)<=len(allowed):path.append(u);u=parents[u]
        path.reverse()
    distance=generalized=exposure=eta=0.;segments=[]
    for u,v in zip(path,path[1:]):
        row=next((e for e in edges.get(u,[]) if e[0]==v),None)
        if row is None:raise RuntimeError('Invalid path reconstruction')
        _,d,k,name=row;distance+=d;generalized+=cost(u,v,d,k);exposure+=d*risk_level(u,v,k);eta+=d*conditions(u,v,k)[2]
        segments.append({'name':name,'km':round(d,4),'cost':round(cost(u,v,d,k),4),'risk':round(risk_level(u,v,k),3)})
    return {'algorithm':algorithm,'path':path,'explored':explored[:5000],'expanded':len(explored),'distance':round(distance,4) if found else None,'cost':round(generalized,4) if found else None,'risk':round(exposure,4) if found else None,'eta_minutes':round(eta,1) if found else None,'scenario':{'incident':incident,'time_of_day':time_of_day,'weather':weather,'priority':priority,'vehicle':vehicle,'traffic':traffic},'steps':len(path)-1 if found else None,'segments':segments,'runtime_ms':round((time.perf_counter()-t0)*1000,3),'frontier_peak':frontier_peak,'trace':trace,'optimality':'minimum edge count' if algorithm in ('bfs','bidirectional','ids') else 'minimum objective cost' if algorithm in ('ucs','astar') else 'not guaranteed','message':None if found else 'No route within selected limits; try another algorithm or remove blocks.'}
