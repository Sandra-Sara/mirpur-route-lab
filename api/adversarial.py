"""Educational route resilience game. No live disruption or dispatch."""
import heapq, math, random, time
from functools import lru_cache

ALGS=('minimax','alphabeta','mcts')
HAZARDS=('clear','congestion','waterlogging','closure','false_report')

def shortest(g,s,t,penalty):
    q=[(0,s)]; dist={s:0}; prev={}; expanded=0
    while q:
        d,u=heapq.heappop(q)
        if d!=dist[u]: continue
        expanded+=1
        if u==t:
            path=[u]; km=0
            while u!=s:
                u,w=prev[u];path.append(u);km+=w
            return list(reversed(path)),km,expanded
        for v,w,*_ in g['edges'].get(u,[]):
            if v not in g['nodes'] or w<=0: continue
            nd=d+w*penalty.get((u,v),1)
            if nd<dist.get(v,math.inf):
                dist[v]=nd;prev[v]=(u,w);heapq.heappush(q,(nd,v))
    return [],0,expanded

def candidates(g,s,t):
    result=[]; penalty={}; expansions=0
    for _ in range(6):
        p,km,n=shortest(g,s,t,penalty); expansions+=n
        if not p: break
        if p not in [x[0] for x in result]: result.append((p,km))
        for e in zip(p,p[1:]): penalty[e]=penalty.get(e,1)*2.2
        if len(result)==3:break
    return result,expansions

class Game:
    def __init__(self,routes,level,seed):
        self.routes=routes;self.level=level;self.seed=seed
        self.edges=[set(zip(p,p[1:])) for p,_ in routes]
        self.risk=[sum(random.Random(f'{seed}:{u}:{v}').uniform(.05,.45) for u,v in e)/max(1,len(e)) for e in self.edges]
        # Fixed, reproducible simulated exposure segments, never live reports.
        self.zones=[next(iter(sorted(e)),None) for e in self.edges]
    def actions(self,state,ply):
        if ply%2==1:return list(range(len(self.routes)))
        return list(range(len(HAZARDS)))
    def step(self,state,ply,a):
        route,hazards,switches=state
        if ply%2==1:return a,hazards,switches+int(route!=a and route>=0)
        return route,hazards+((route,a),),switches
    def metrics(self,state):
        route,events,switches=state;route=max(0,route)
        p,km=self.routes[route]; traffic=0; water=0; blocked=False; false=0
        for target,h in events:
            # Overlapping routes share exposure to the same simulated segment.
            if self.zones[target] not in self.edges[route]:continue
            if h==1:traffic+=.65*self.level
            elif h==2:water+=.45*self.level
            elif h==3:blocked=True
            elif h==4:false+=1
        eta=km/30*60*(1+traffic+water)+.25*switches+.5*false
        risk=min(1,self.risk[route]+.1*water+.05*traffic)
        utility=-(eta+4*risk+100*blocked)
        return dict(route=route,distance=km,eta=None if blocked else eta,safety=100*(1-risk),utility=utility,blocked=blocked,false_reports=false)
    def label(self,ply,a):return f'Route {a+1}' if ply%2==1 else HAZARDS[a]

def solve(game,algorithm,depth,rollouts,seed):
    start=time.perf_counter(); initial=(0,(),0); trace=[]; expanded=0; leaves=0; pruned=0; rng=random.Random(seed)
    def visit(state,ply,alpha,beta,parent,action):
        nonlocal expanded,leaves,pruned
        idx=len(trace); trace.append(dict(id=idx,parent=parent,ply=ply,agent='MAX' if ply%2==1 else 'MIN',action=action,status='visited'))
        if ply==depth:
            leaves+=1; val=game.metrics(state)['utility'];trace[idx]['value']=val;return val,[]
        expanded+=1; maximize=ply%2==1;best=-math.inf if maximize else math.inf;pv=[];acts=game.actions(state,ply)
        for i,a in enumerate(acts):
            val,path=visit(game.step(state,ply,a),ply+1,alpha,beta,idx,game.label(ply,a))
            if (val>best if maximize else val<best):best=val;pv=[a]+path
            if maximize:alpha=max(alpha,best)
            else:beta=min(beta,best)
            if algorithm=='alphabeta' and alpha>=beta:
                for omitted in acts[i+1:]:
                    pruned+=1;trace.append(dict(id=len(trace),parent=idx,ply=ply+1,agent='MIN' if maximize else 'MAX',action=game.label(ply,omitted),status='pruned'))
                break
        trace[idx]['value']=best;return best,pv
    if algorithm!='mcts':value,pv=visit(initial,0,-math.inf,math.inf,None,'root')
    else:
        # UCT: MAX maximizes mean reward, MIN minimizes it; rollout uses uniform legal actions.
        tree=[dict(state=initial,ply=0,parent=None,a=None,n=0,total=0.,children={})]
        for _ in range(rollouts):
            i=0
            while tree[i]['ply']<depth:
                node=tree[i];p=node['ply'];acts=game.actions(node['state'],p);missing=[a for a in acts if a not in node['children']]
                if missing:
                    a=rng.choice(missing);j=len(tree);node['children'][a]=j;tree.append(dict(state=game.step(node['state'],p,a),ply=p+1,parent=i,a=a,n=0,total=0.,children={}));i=j;expanded+=1;break
                sign=1 if p%2==1 else -1
                i=max(node['children'].values(),key=lambda j:sign*tree[j]['total']/tree[j]['n']+20*math.sqrt(math.log(max(1,node['n']))/tree[j]['n']))
            state=tree[i]['state'];p=tree[i]['ply']
            for k in range(p,depth):state=game.step(state,k,rng.choice(game.actions(state,k)))
            val=game.metrics(state)['utility'];leaves+=1
            while i is not None:
                tree[i]['n']+=1;tree[i]['total']+=val;i=tree[i]['parent']
        i=0;pv=[]
        while tree[i]['children']:
            a,i=max(tree[i]['children'].items(),key=lambda item:tree[item[1]]['n']);pv.append(a)
        state=initial
        for p,a in enumerate(pv):state=game.step(state,p,a)
        for p in range(len(pv),depth):
            a=max(game.actions(state,p),key=lambda a:(1 if p%2==1 else -1)*game.metrics(game.step(state,p,a))['utility']);pv.append(a);state=game.step(state,p,a)
        value=tree[0]['total']/tree[0]['n']
        trace=[dict(id=i,parent=n['parent'],ply=n['ply'],agent='MAX' if n['ply']%2==1 else 'MIN',action='root' if n['a'] is None else game.label(n['ply']-1,n['a']),status='visited',value=n['total']/n['n'],visits=n['n']) for i,n in enumerate(tree)]
    state=initial; decisions=[]
    for p,a in enumerate(pv):
        state=game.step(state,p,a);decisions.append(dict(ply=p+1,agent='MAX' if p%2==1 else 'MIN',action=game.label(p,a),utility=game.metrics(state)['utility']))
    metrics=game.metrics(state)
    return dict(algorithm=algorithm,value=value,expanded=expanded,leaves=leaves,pruned=pruned,runtime_ms=(time.perf_counter()-start)*1000,metrics=metrics,decisions=decisions,trace=trace,events=[dict(route=r,hazard=HAZARDS[h]) for r,h in state[1]])

def register(app,fetch_roads):
    from flask import request,jsonify,send_from_directory
    import os
    @app.get('/adversarial')
    def adversarial_page():return send_from_directory(os.path.join(os.path.dirname(os.path.dirname(__file__)),'static'),'adversarial.html')
    @app.post('/api/adversarial')
    def adversarial_api():
        try:
            p=request.get_json();depth=int(p.get('depth',4));rollouts=int(p.get('rollouts',300));seed=int(p.get('seed',42));level=float(p.get('level',.6))
            if depth not in (2,4,6) or not 30<=rollouts<=1500 or not .1<=level<=1:raise ValueError('Invalid simulation parameters')
            g=fetch_roads();nodes=g['nodes']
            def nearest(pos):
                lat,lon=map(float,pos)
                if not math.isfinite(lat+lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Invalid coordinates')
                return min(nodes,key=lambda k:(nodes[k][0]-lat)**2+((nodes[k][1]-lon)*math.cos(math.radians(lat)))**2)
            s,t=nearest(p['start']),nearest(p['end'])
            if s==t:raise ValueError('Select different road nodes')
            routes,n=candidates(g,s,t)
            if not routes:raise ValueError('No directed route found in existing graph')
            game=Game(routes,level,seed);results=[solve(game,a,depth,rollouts,seed) for a in ALGS]
            # Same candidate routes, seed and depth for all algorithms and repeated random trials.
            rng=random.Random(seed);trials=[]
            for i in range(30):
                hazards=[(rng.randrange(len(routes)),rng.randrange(len(HAZARDS))) for _ in range(depth//2)]
                for r in results:
                    trials.append(dict(trial=i+1,algorithm=r['algorithm'],utility=game.metrics((int(r['decisions'][1]['action'].split()[-1])-1,tuple(hazards),0))['utility']))
            return jsonify(source=g.get('source','Unknown'),simulated=g.get('simulated',False),graph_nodes=len(nodes),route_expansions=n,routes=[dict(coordinates=[nodes[x] for x in path],km=km,zone=[nodes[x] for x in game.zones[i]]) for i,(path,km) in enumerate(routes)],results=results,trials=trials)
        except (ValueError,KeyError,TypeError) as e:return jsonify(error=str(e)),400
        except Exception as e:return jsonify(error=str(e)),503
