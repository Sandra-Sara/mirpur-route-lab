import unittest
from api.search import route_search
try:
    from api.index import app
except ModuleNotFoundError:
    app=None

class Advanced(unittest.TestCase):
    def test_bidir_shortest_edge_count(self):
        nodes={str(i):[23.8+i*.00001,90.3] for i in range(9)}
        edges={'0':[['1',1,'primary',''],['3',1,'primary','']], '1':[['2',1,'primary','']], '2':[['4',1,'primary','']], '3':[['4',1,'primary','']], '4':[['5',1,'primary','']]}
        graph={'nodes':nodes,'edges':edges}
        for alg in ('bfs','bidirectional','ids'):
            with self.subTest(alg=alg):self.assertEqual(route_search(graph,'0','5',algorithm=alg,depth=10)['steps'],3)
    def test_trace_records_frontier(self):
        g={'nodes':{'a':[23.8,90.3],'b':[23.81,90.3]},'edges':{'a':[['b',1,'primary','Road']]}}
        for alg in ('bfs','dfs','dls','ids','ucs','bidirectional','greedy','astar','weighted','beam'):
            with self.subTest(alg=alg):
                x=route_search(g,'a','b',algorithm=alg)
                self.assertTrue(x['trace'])
                self.assertIn('frontier',x['trace'][0])
    @unittest.skipIf(app is None, "Flask unavailable; install requirements to test HTTP routes")
    def test_flask_home_and_health(self):
        c=app.test_client()
        self.assertEqual(c.get('/').status_code,200)
        self.assertIn(b'MIRPUR',c.get('/').data)
        self.assertEqual(c.get('/api/health').json['ok'],True)
    def test_weighted_cost_bound_not_negative(self):
        g={'nodes':{'a':[23.8,90.3],'b':[23.81,90.3]},'edges':{'a':[['b',1,'primary','Road']]}}
        x=route_search(g,'a','b',traffic=3,risk=3)
        self.assertGreaterEqual(x['cost'],x['distance'])
if __name__=='__main__':unittest.main()
