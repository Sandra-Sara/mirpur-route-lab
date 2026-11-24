import unittest
from api.adversarial import Game,solve,candidates,register

def graph():return {'nodes':{'s':[23.8,90.3],'a':[23.81,90.31],'b':[23.81,90.32],'t':[23.82,90.33]},'edges':{'s':[['a',1],['b',1.1]],'a':[['t',1]],'b':[['t',1.1]]},'source':'synthetic test','simulated':True}
class AdversarialTests(unittest.TestCase):
    def test_directed_paths(self):
        paths,_=candidates(graph(),'s','t');self.assertEqual(len(paths),2);self.assertEqual(candidates(graph(),'t','s')[0],[])
    def test_exact_equivalence(self):
        game=Game(candidates(graph(),'s','t')[0],.6,42)
        for depth in (2,4,6):
            a=solve(game,'minimax',depth,300,42);b=solve(game,'alphabeta',depth,300,42)
            self.assertAlmostEqual(a['value'],b['value']);self.assertLessEqual(b['expanded'],a['expanded']);self.assertEqual(a['value'],a['metrics']['utility'])
    def test_mcts_reproducibility(self):
        g=Game(candidates(graph(),'s','t')[0],.6,42);a=solve(g,'mcts',4,100,42);b=solve(g,'mcts',4,100,42)
        self.assertEqual(a['trace'],b['trace']);self.assertEqual(a['leaves'],100);self.assertEqual(len(a['decisions']),4)
    def test_closure_and_recovery(self):
        g=Game(candidates(graph(),'s','t')[0],.6,42);s=g.step((0,(),0),0,3);self.assertTrue(g.metrics(s)['blocked']);self.assertFalse(g.metrics(g.step(s,1,1))['blocked'])
    def test_http(self):
        try: from flask import Flask
        except ImportError: self.skipTest("Flask not installed")
        app=Flask(__name__);register(app,graph);c=app.test_client();r=c.post('/api/adversarial',json={'start':[23.8,90.3],'end':[23.82,90.33]});self.assertEqual(r.status_code,200,r.get_data(as_text=True));self.assertEqual(len(r.json['results']),3);self.assertEqual(len(r.json['trials']),90);self.assertTrue(r.json['simulated'])
        self.assertEqual(c.post('/api/adversarial',json={'depth':99}).status_code,400)
