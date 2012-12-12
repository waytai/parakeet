
import testing_helpers 
import mutability_analysis
import lowering 

def f():
  x = slice(1, 2, None)
  x.start = 10
  x.stop = 20 
  
def test_mutable_slice():
  _, typed, _, _ =  testing_helpers.specialize_and_compile(f, [])
  mutable_types = mutability_analysis.find_mutable_types(typed)
  print "mutable types", mutable_types 
  assert len(mutable_types) == 1, mutable_types 
  lowered = lowering.lower(typed)
  mutable_types = mutability_analysis.find_mutable_types(lowered)
  assert len(mutable_types) == 1, mutable_types
  
if __name__ == '__main__':
  testing_helpers.run_local_tests()