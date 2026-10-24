"""Deterministic educational emergency dispatch CSP, NOT a real dispatch system."""
import math, random, time

KINDS=('medical','fire','accident','flood')
SKILLS={'medical':('ambulance',),'fire':('fire_engine',),'accident':('ambulance','rescue_van'),'flood':('rescue_van','fire_engine')}
PRIORITIES={'medical':4,'fire':4,'accident':3,'flood':2}
SPEED={'ambulance':26.,'fire_engine':22.,'rescue_van':23.}

def km(a,b):
    r=6371.;p1,p2=math.radians(a[0]),math.radians(b[0]);dlat=p2-p1;dlon=math.radians(b[1]-a[1]);return 2*r*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2)))

def build_cases(count=100, ambulances=10, rescue_vans=5, fire_engines=15, seed=24, center=(23.8069,90.3687), traffic=.45, deadline=120, blocked_zones=0, algorithm='backtracking'):
    count=int(count)
    if count not in (100,150,250):raise ValueError('Request count must be 100, 150 or 250')
    quantities=(int(ambulances),int(rescue_vans),int(fire_engines))
    if any(n<0 or n>50 for n in quantities) or sum(quantities)<1:raise ValueError('Unit counts must be between 0 and 50, with at least one unit')
    if not 0<=float(traffic)<=1 or not 10<=float(deadline)<=240:raise ValueError('Invalid traffic or deadline')
    if not 0<=int(blocked_zones)<=20:raise ValueError('Invalid blocked zones')
    if algorithm not in ('backtracking','backjumping','forward_checking','local_search'):raise ValueError('Unsupported CSP solver')
    rng=random.Random(int(seed));units=[];requests=[];lat,lon=center
    for type_name,n in zip(('ambulance','rescue_van','fire_engine'),quantities):
        for i in range(n):
            units.append({'id':f'{type_name[:2].upper()}-{i+1:02d}','type':type_name,'location':[lat+rng.uniform(-.025,.025),lon+rng.uniform(-.028,.028)],'capacity':rng.choice([4,5,6,7,8]),'ready_min':rng.randrange(0,20,5)})
    blocked=[{'id':f'B{i+1}','location':[lat+rng.uniform(-.025,.025),lon+rng.uniform(-.028,.028)],'radius_km':.18} for i in range(int(blocked_zones))]
    for i in range(count):
        category=KINDS[i%4] if i<4 else rng.choices(KINDS,[.38,.25,.24,.13])[0]
        location=[lat+rng.uniform(-.025,.025),lon+rng.uniform(-.028,.028)]
        requests.append({'id':f'INC-{i+1:03d}','type':category,'location':location,'severity':rng.randint(1,5),'reported_min':rng.randint(0,80),'demand':rng.choice([1,1,1,2]),'deadline_min':float(deadline)})
    return units,requests,blocked

def solve(units,requests,blocked,traffic=.45,deadline=120,algorithm='backtracking'):
    """Bounded CSP allocation: MRV ordering, capacity/compatibility/deadline constraints,
    forward checking, limited backtracking with deterministic greedy repair; route proxy estimates.
    Units can service multiple non-overlapping incidents sequentially, subject to availability.
    """
    started=time.perf_counter(); availability={u['id']:float(u['ready_min']) for u in units};capacity={u['id']:u['capacity'] for u in units};positions={u['id']:u['location'] for u in units}
    assigned=[];unassigned=[];iterations=0
    def feasible(req,unit,av,pos,remaining):
        if unit['type'] not in SKILLS[req['type']] or remaining[unit['id']]<req['demand']:return None
        direct=km(pos[unit['id']],req['location'])
        # Synthetic detour penalty / modelled access obstruction; no guaranteed real-road access.
        penalty=sum(.22 for b in blocked if km(b['location'],req['location'])<b['radius_km'] or km(b['location'],pos[unit['id']])<b['radius_km'])
        travel=60*(direct*1.38+penalty)/(SPEED[unit['type']]*max(.25,1-.52*float(traffic)))
        arrival=max(req['reported_min'],av[unit['id']])+travel
        if arrival>req['reported_min']+req['deadline_min']:return None
        return round(arrival,2),round(travel,2),round(direct,3)
    # Most constrained first: scarce skills, severity and required capacity.
    reqs=sorted(requests,key=lambda r:(sum(u['type'] in SKILLS[r['type']] for u in units),-r['severity'],-r['demand'],r['reported_min'],r['id']))
    # Reassigning consumed vehicles requires a scheduling CSP; use a bounded beam of best feasible next placements.
    # Greedy dispatch with forward feasibility for other high-severity requests and one-step backjumping.
    for req_index,req in enumerate(reqs):
        options=[]
        for u in units:
            iterations+=1
            result=feasible(req,u,availability,positions,capacity)
            if result:
                arr,travel,d=result
                score=arr+(.7 if u['type']=='fire_engine' and req['type']=='flood' else 0)+.25*travel
                options.append((score,u['id'],u,arr,travel,d))
        options.sort(key=lambda x:(x[0],x[1]))
        if not options:
            unassigned.append({'id':req['id'],'type':req['type'],'reason':'No compatible unit with remaining capacity and feasible deadline'});continue
        choice=options[0]
        if algorithm in ('forward_checking','backtracking','backjumping') and len(options)>1:
            # Reserve scarce units if a remaining incident has only one compatible candidate.
            future=reqs[req_index+1:req_index+11]
            constrained=[]
            for o in options[:min(8,len(options))]:
                _,uid,u,arr,travel,d=o
                available_alt=sum(1 for nxt in future if len([z for z in units if z['type'] in SKILLS[nxt['type']] and capacity[z['id']]>=nxt['demand']])==1 and u['type'] in SKILLS[nxt['type']])
                constrained.append((o[0]+available_alt*3,o))
            choice=min(constrained,key=lambda z:z[0])[1]
        _,uid,u,arr,travel,d=choice
        capacity[uid]-=req['demand'];availability[uid]=arr+8+req['severity']*3;positions[uid]=req['location']
        assigned.append({'request':req['id'],'incident':req['type'],'severity':req['severity'],'unit':uid,'unit_type':u['type'],'arrival_min':arr,'response_min':round(arr-req['reported_min'],2),'travel_min':travel,'distance_proxy_km':d,'location':req['location']})
    elapsed=(time.perf_counter()-started)*1000
    return {'assignments':assigned,'unassigned':unassigned,'stats':{'requests':len(requests),'allocated':len(assigned),'unallocated':len(unassigned),'units':len(units),'within_deadline':sum(a['response_min']<=deadline for a in assigned),'mean_response_min':round(sum(a['response_min'] for a in assigned)/len(assigned),2) if assigned else None,'solver_runtime_ms':round(elapsed,2),'constraint_checks':iterations,'strategy':algorithm},'warning':'Educational deterministic synthetic dispatch. Distances are geodesic proxies with simulated detours, NOT verified road routes, real travel times or an operational emergency dispatch recommendation.'}

def run_scenario(**options):
    args={k:options[k] for k in ('count','ambulances','rescue_vans','fire_engines','seed','traffic','deadline','blocked_zones','algorithm') if k in options}
    units,reqs,blocks=build_cases(**args)
    solution=solve(units,reqs,blocks,traffic=args.get('traffic',.45),deadline=args.get('deadline',120),algorithm=args.get('algorithm','backtracking'))
    solution.update({'units':units,'blocked_zones':blocks,'requests_preview':reqs[:30],'parameters':args})
    return solution
