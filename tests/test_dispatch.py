import unittest
from api.dispatch import build_cases, solve, run_scenario, SKILLS

class DispatchTests(unittest.TestCase):
 def test_sizes(self):
  for n in (100,150,250):
   r=run_scenario(count=n,ambulances=10,rescue_vans=5,fire_engines=15)
   self.assertEqual(r['stats']['requests'],n)
   self.assertEqual(r['stats']['allocated']+r['stats']['unallocated'],n)
 def test_deterministic(self):
  a=run_scenario(count=100,seed=17);b=run_scenario(count=100,seed=17)
  self.assertEqual(a['assignments'],b['assignments'])
 def test_skill_constraints(self):
  r=run_scenario(count=150)
  self.assertTrue(all(x['unit_type'] in SKILLS[x['incident']] for x in r['assignments']))
 def test_deadline(self):
  r=run_scenario(count=250,deadline=60)
  self.assertTrue(all(x['response_min']<=60.001 for x in r['assignments']))
 def test_exhausted_units(self):
  r=run_scenario(count=100,ambulances=0,rescue_vans=0,fire_engines=1)
  self.assertGreater(r['stats']['unallocated'],0)
 def test_invalid(self):
  with self.assertRaises(ValueError):run_scenario(count=101)
if __name__=='__main__':unittest.main()
