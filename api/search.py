"""Deterministic directed road-graph search algorithms (educational simulation)."""
from collections import deque
import heapq, math, time

LIMIT=50000

def haversine(a,b):
    lat1,lon1=map(math.radians,a);lat2,lon2=map(math.radians,b)
    x=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742*math.asin(min(1,math.sqrt(x)))

def route_search(graph,start,goal,algorithm='astar',mode='weighted',traffic=.6,risk=.5,blocked=None,weight=1.5,depth=60,beam=25,allowed=None):
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
    def cost(u,v,d,kind):
        q=risk_level(u,v,kind);c=.65 if kind in ('primary','secondary','trunk') else .25
        congestion=c+.35*(q%1)
        return d if mode=='distance' else d*(1+traffic*congestion+risk*q)
    def neighbor(u):
        for v,d,k,name in edges.get(u,[]):
            if v in allowed and frozenset((u,v)) not in blocked:
                yield v,d,k,name,cost(u,v,d,k)
    explored=[]; parents={start:None};found=False;frontier_peak=1
    def capped():return len(explored)>=LIMIT
    if start==goal:found=True;explored.append(start)
    elif algorithm=='bfs':
        q=deque([start]);seen={start}
        while q and not capped():
            frontier_peak=max(frontier_peak,len(q));u=q.popleft();explored.append(u)
            if u==goal:found=True;break
            for v,*_ in neighbor(u):
                if v not in seen:seen.add(v);parents[v]=u;q.append(v)
    elif algorithm in ('dfs','dls','ids'):
        def visit(limit):
            # Path-specific cycle detection allows alternative paths; depth-reach pruning is sound for DLS.
            stack=[(start,0,(start,))];local={start:None};expanded=[];best={start:0};peak=1
            while stack and len(expanded)<LIMIT:
                peak=max(peak,len(stack));u,level,path=stack.pop();expanded.append(u)
                if u==goal:
                    return list(path),expanded,peak
                if level>=limit:continue
                children=list(neighbor(u));children.reverse()
                for v,*_ in children:
                    if v not in path and level+1 < best.get(v,math.inf):
                        best[v]=level+1;stack.append((v,level+1,path+(v,)))
            return None,expanded,peak
        if algorithm=='ids':
            for limit in range(depth+1):
                p,e,pk=visit(limit);explored.extend(e);frontier_peak=max(frontier_peak,pk)
                if p:found=True;break
                if capped():break
        else:
            # DFS is unrestricted relative to the graph size, DLS honors the input bound
            p,explored,frontier_peak=visit((len(allowed)-1) if algorithm=='dfs' else depth)
            found=bool(p)
        if found:
            parents={p[0]:None}
            for a,b in zip(p,p[1:]):parents[b]=a
    elif algorithm=='bidirectional':
        reverse={}
        for u in allowed:
            for v,*_ in neighbor(u):reverse.setdefault(v,[]).append(u)
        qa=deque([start]);qb=deque([goal]);pa={start:None};pb={goal:None};meet=None
        while qa and qb and not capped():
            forward=len(qa)<=len(qb)
            q,own,other=(qa,pa,pb) if forward else (qb,pb,pa)
            for _ in range(len(q)):
                u=q.popleft();explored.append(u)
                if u in other:meet=u;break
                adjacent=(v for v,*_ in neighbor(u)) if forward else iter(reverse.get(u,[]))
                for v in adjacent:
                    if v not in own:own[v]=u;q.append(v)
                    if v in other:meet=v;break
                if meet is not None:break
                if capped():break
            frontier_peak=max(frontier_peak,len(qa)+len(qb))
            if meet is not None:break
        if meet is not None:
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
                explored.append(u)
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
            frontier_peak=max(frontier_peak,len(pq));priority,_,u=heapq.heappop(pq)
            if u in closed:continue
            closed.add(u);explored.append(u)
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
    distance=generalized=exposure=0.;segments=[]
    for u,v in zip(path,path[1:]):
        row=next((e for e in edges.get(u,[]) if e[0]==v),None)
        if row is None:raise RuntimeError('Invalid path reconstruction')
        _,d,k,name=row;distance+=d;generalized+=cost(u,v,d,k);exposure+=d*risk_level(u,v,k)
        segments.append({'name':name,'km':round(d,4),'cost':round(cost(u,v,d,k),4),'risk':round(risk_level(u,v,k),3)})
    return {'algorithm':algorithm,'path':path,'explored':explored[:5000],'expanded':len(explored),'distance':round(distance,4) if found else None,'cost':round(generalized,4) if found else None,'risk':round(exposure,4) if found else None,'steps':len(path)-1 if found else None,'segments':segments,'runtime_ms':round((time.perf_counter()-t0)*1000,3),'frontier_peak':frontier_peak,'optimality':'minimum edge count' if algorithm in ('bfs','bidirectional','ids') else 'minimum objective cost' if algorithm in ('ucs','astar') else 'not guaranteed','message':None if found else 'No route within selected limits; try another algorithm or remove blocks.'}
