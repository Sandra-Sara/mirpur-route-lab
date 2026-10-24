import unittest
from api.search import route_search

class DispatchScenarios(unittest.TestCase):
    def setUp(self):
        self.g={'nodes':{'a':[23.80,90.36],'b':[23.81,90.37],'c':[23.82,90.38]},'edges':{'a':[['b',1,'primary','A']], 'b':[['c',1,'residential','B']], 'c':[]}}
    def test_controls_affect_actual_metrics(self):
        base=route_search(self.g,'a','c',traffic=.15,time_of_day='night',weather='summer',vehicle='police_patrol')
        high=route_search(self.g,'a','c',traffic=.85,time_of_day='evening',weather='monsoon',vehicle='fire_engine')
        self.assertNotEqual(base['eta_minutes'],high['eta_minutes'])
        self.assertNotEqual(base['cost'],high['cost'])
    def test_priority_changes_cost(self):
        a=route_search(self.g,'a','c',priority='balanced')
        b=route_search(self.g,'a','c',priority='avoid_congestion')
        self.assertNotEqual(a['cost'],b['cost'])
    def test_validate_invalid_scenario(self):
        with self.assertRaises(ValueError):route_search(self.g,'a','c',weather='tornado')
