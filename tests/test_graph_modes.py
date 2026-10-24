import unittest
from api.search import route_search
class GraphModes(unittest.TestCase):
    def test_all_graph_objectives_return_finite_nonnegative_metrics(self):
        g={'nodes':{'a':[23.8,90.36],'b':[23.801,90.361],'c':[23.802,90.362]},'edges':{'a':[['b',.2,'residential','X']],'b':[['c',.3,'residential','Y']]}}
        for mode in ('distance','time','safety','composite'):
            for traffic in (.15,.45,.85):
                r=route_search(g,'a','c',mode=mode,traffic=traffic)
                self.assertEqual(r['steps'],2)
                self.assertGreater(r['cost'],0)
                self.assertGreater(r['eta_minutes'],0)
if __name__=='__main__':unittest.main()
