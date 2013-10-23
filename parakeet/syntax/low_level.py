from expr import Expr 

class Struct(Expr):
  """
  Eventually all non-scalar data should be transformed to be created with this
  syntax node, signifying explicit struct allocation
  """

  _members = ['args']

  def __str__(self):
    return "Struct(%s) : %s" % \
           (", ".join(str(arg) for arg in self.args), self.type)

  def children(self):
    return self.args

  def __hash__(self):
    self.args = tuple(self.args)
    return hash(self.args)

class Alloc(Expr):
  """Allocates a block of data, returns a pointer"""

  _members = ['elt_type', 'count']

  def __str__(self):
    return "alloc<%s>[%s] : %s" % (self.elt_type, self.count, self.type)

  def children(self):
    return (self.count,)

  def __hash__(self):
    return hash((self.elt_type, self.count))
  
class NumCores(Expr):
  
  """
  Degree of available parallelism, 
  varies depending on backend and how
  ParFor is actually being mapped 
  to executing threads/thread blocks/etc..
  """
  _members = []
  
  def __str__(self):
    return "NUM_CORES"
  
  def __eq__(self, other):
    return other.__class__ is NumCores 
  
  def node_init(self):
    from ..ndtypes import Int64
    self.type = Int64 
  
  def __hash__(self):
    return 0
  
  def children(self):
    return ()
  
  