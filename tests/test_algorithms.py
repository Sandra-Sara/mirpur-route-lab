import unittest
from api.search import route_search

N={'A':[23.8,90.36],'B':[23.801,90.36],'C':[23.8,90.361],'D':[23.801,90.361],'E':[23.802,90.362]}
E={'A':[['B',1,'primary','AB'],['C',2,'residential','AC']], 'B':[['D',1,'primary','BD']], 'C':[['D',3,'residential','CD']], 'D':[['E',1,'primary','DE']]}
G={'nodes':N,'edges':E}
class Algorithms(unittest.TestCase):
    def test_all_find_directed_path(self):
        for alg in ('bfs','dfs','dls','ids','ucs','bidirectional','greedy','astar','weighted','beam'):
            with self.subTest(alg=alg):
                r=route_search(G,'A','E',algorithm=alg,depth=10,beam=3,mode='distance')
                self.assertEqual(r['path'][0],'A');self.assertEqual(r['path'][-1],'E');self.assertTrue(r['runtime_ms']>=0)
    def test_optimal_cost(self):
        for alg in ('ucs','astar'):
            self.assertEqual(route_search(G,'A','E',algorithm=alg,mode='distance')['cost'],3)
    def test_depth_limit(self):
        self.assertFalse(route_search(G,'A','E',algorithm='dls',depth=2)['path'])
    def test_block(self):
        r=route_search(G,'A','E',algorithm='ucs',mode='distance',blocked={frozenset(('A','B'))})
        self.assertEqual(r['cost'],6)
    def test_direction(self):
        for alg in ('ucs','bidirectional'):
            self.assertFalse(route_search(G,'E','A',algorithm=alg)['path'])
    def test_start_goal(self):
        self.assertEqual(route_search(G,'A','A')['cost'],0)
if __name__=='__main__':unittest.main()
