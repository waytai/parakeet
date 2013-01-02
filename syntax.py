import args
import core_types

from args import ActualArgs
from node import Node

class Stmt(Node):
  pass

def block_to_str(stmts):
  body_str = '\n'
  body_str += '\n'.join([str(stmt) for stmt in stmts])

  return body_str.replace('\n', '\n    ')

def phi_nodes_to_str(phi_nodes):
  parts = ["%s <- phi(%s, %s)" %
           (var, left, right) for (var, (left, right)) in phi_nodes.items()]
  whole = "\n" + "\n".join(parts)
  # add tabs
  return whole.replace("\n", "\n    ")

class Assign(Stmt):
  _members = ['lhs', 'rhs']

  def __str__(self):
    if hasattr(self.lhs, 'type') and self.lhs.type:
      return "%s : %s = %s" % (self.lhs, self.lhs.type, self.rhs)
    else:
      return "%s = %s" % (self.lhs, self.rhs)

class RunExpr(Stmt):
  """Run an expression without binding any new variables"""

  _members = ['value']

  def __str__(self):
    assert self.value is not None 
    return "RunExpr(%s)" % self.value 
  
class Return(Stmt):
  _members = ['value']

  def __str__(self):
    return "Return %s" % self.value

class If(Stmt):
  _members = ['cond', 'true', 'false', 'merge']

  def __str__(self):
    s = "if %s:" % self.cond
    if (len(self.true) + len(self.false)) > 0:
      s += "%s\n" % block_to_str(self.true)
    else:
      s += "\n"
    if len(self.false) > 0:
      s += "else:%s\n" % block_to_str(self.false)
    if len(self.merge) > 0:
      s += "(merge-if)%s" % phi_nodes_to_str(self.merge)
    return s

  def __repr__(self):
    return str(self)

class While(Stmt):
  """
  A loop consists of a header, which runs before each iteration, a condition for
  continuing, the body of the loop, and optionally (if we're in SSA) merge nodes
  for incoming and outgoing variables of the form
  [(new_var1, (old_var1,old_var2)]
  """

  _members = ['cond', 'body', 'merge']

  def __repr__(self):
    s = "while %s:\n  "  % self.cond
    if len(self.merge) > 0:
      s += "(header)%s\n  " % phi_nodes_to_str(self.merge)
    if len(self.body) > 0:
      s +=  "(body)%s" % block_to_str(self.body)
    return s

  def __str__(self):
    return repr(self)

class Expr(Node):
  _members = ['type']

  def children(self):
    for v in self.itervalues():
      if v and isinstance(v, Expr):
        yield v
      elif isinstance(v, (list,tuple)):
        for child in v:
          if isinstance(child, Expr):
            yield child

class Const(Expr):
  _members = ['value']

  def children(self):
    return (self.value,)

  def __repr__(self):
    if self.type and not isinstance(self.type, core_types.NoneT):
      return "%s : %s" % (self.value, self.type)
    else:
      return str(self.value)

  def __str__(self):
    return repr(self)

  def __hash__(self):
    return hash(self.value)

  def __eq__(self, other):
    return self.__class__ == other.__class__ and \
           self.type == other.type and \
           self.value == other.value

class Var(Expr):
  _members = ['name']

  def __repr__(self):
    if hasattr(self, 'type'):
      return "%s : %s" % (self.name, self.type)
    else:
      return "%s" % self.name

  def __str__(self):
    return self.name

  def __hash__(self):
    return hash(self.name)

  def __eq__(self, other):
    return self.__class__ == other.__class__ and \
           self.type == other.type and \
           self.name == other.name

  def children(self):
    return ()

class Attribute(Expr):
  _members = ['value', 'name']

  def children(self):
    yield self.value

  def __str__(self):
    return "attr(%s, '%s')" % (self.value, self.name)

  def __hash__(self):
    return hash ((self.value, self.name))

  def __eq__(self, other):
    return isinstance(other, Attribute) and \
           self.name == other.name and \
           self.value == other.value

class Index(Expr):
  _members = ['value', 'index']

  def children(self):
    yield self.value
    yield self.index

  def __str__(self):
    return "%s[%s]" % (self.value, self.index)

class Tuple(Expr):
  _members = ['elts']

  def __str__(self):
    if len(self.elts) > 0:
      return ", ".join([str(e) for e in self.elts])
    else:
      return "()"

  def node_init(self):
    self.elts = tuple(self.elts)

  def children(self):
    return self.elts

class Array(Expr):
  _members = ['elts']

  def node_init(self):
    self.elts = tuple(self.elts)

  def children(self):
    return self.elts

class Closure(Expr):
  """Create a closure which points to a global fn with a list of partial args"""

  _members = ['fn', 'args']

  def node_init(self):
    self.args = tuple(self.args)

  def children(self):
    if isinstance(self.fn, Expr):
      yield self.fn
    for arg in self.args:
      yield arg

class Call(Expr):
  _members = ['fn', 'args']

  def __str__(self):
    if isinstance(self.fn, (Fn, TypedFn)):
      fn_name = self.fn.name
    else:
      fn_name = str(self.fn)
    if isinstance(self.args, ActualArgs):
      arg_str = str(self.args)
    else:
      arg_str = ", ".join(str(arg) for arg in self.args)
    return "%s(%s)" % (fn_name, arg_str)

  def __repr__(self):
    return str(self)

  def children(self):
    yield self.fn
    for arg in self.args:
      yield arg

class Slice(Expr):
  _members = ['start', 'stop', 'step']

  def __str__(self):
    return "slice(%s,%s,%s)"  % (self.start, self.stop, self.step)

  def __repr__(self):
    return str(self)

  def children(self):
    yield self.start
    yield self.stop
    yield self.step

class PrimCall(Expr):
  """
  Call a primitive function, the "prim" field should be a prims.Prim object
  """

  _members = ['prim', 'args']

  def __repr__(self):
    if self.prim.symbol:
      if len(self.args) == 1:
        return "%s %s" % (self.prim.symbol)
      else:
        assert len(self.args) == 2
        return "%s %s %s" % (self.args[0], self.prim.symbol, self.args[1])
    else:
      return "prim<%s>(%s)" % (self.prim.name, ", ".join(map(str, self.args)))

  def __str__(self):
    return repr(self)

  def __hash__(self):
    return hash((self.prim, self.args))

  def node_init(self):
    self.args = tuple(self.args)

  def children(self):
    return self.args

############################################################################
#
#  Array Operators: It's not scalable to keep adding first-order operators
#  at the syntactic level, so eventually we'll need some more extensible
#  way to describe the type/shape/compilation semantics of array operators
#
#############################################################################

class ConstArray(Expr):
  _members = ['shape', 'value']

class ConstArrayLike(Expr):
  """
  Create an array with the same shape as the first arg, but with all values set
  to the second arg
  """

  _members = ['array', 'value']

class ArrayView(Expr):
  """Create a new view on already allocated underlying data"""

  _members = ['data', 'shape', 'strides', 'offset', 'total_elts']

  def children(self):
    yield self.data
    yield self.shape
    yield self.strides
    yield self.offset
    yield self.total_elts

class Fn(Expr):
  """
  Function definition.
  A top-level function can have references to python values from its enclosing
  scope, which are stored in the 'python_refs' field.

  A nested function, on the other hand, might refer to some variables from its
  enclosing Parakeet scope, whose original names are stored in
  'parakeet_nonlocals'
  """

  _members = ['name', 'args', 'body', 'python_refs', 'parakeet_nonlocals']
  registry = {}

  def __str__(self):
    return "Fn(%s)" % self.name
    # return repr(self)

  def __repr__(self):
    return "def %s(%s):%s" % (self.name, self.args, block_to_str(self.body))

  def __hash__(self):
    return hash(self.name)

  def node_init(self):
    assert isinstance(self.name, str), \
        "Expected string for fn name, got %s" % self.name
    assert isinstance(self.args, args.FormalArgs), \
        "Expected arguments to fn to be FormalArgs object, got %s" % self.args
    assert isinstance(self.body, list), \
        "Expected body of fn to be list of statements, got " + str(self.body)

    import closure_type
    self.type = closure_type.make_closure_type(self.name, ())
    self.registry[self.name] = self

  def python_nonlocals(self):
    if self.python_refs:
      return [ref.deref() for ref in self.python_refs]
    else:
      return []

  def children(self):
    return ()

################################################################################
#
#  Constructs below here are only used in the typed representation
#
################################################################################

class TupleProj(Expr):
  _members = ['tuple', 'index']

  def __str__(self):
    return "%s[%d]" % (self.tuple, self.index)
  
  def children(self):
    return (self.tuple,)

class ClosureElt(Expr):
  _members = ['closure', 'index']

  def __str__(self):
    return "ClosureElt(%s, %d)" % (self.closure, self.index)

  def children(self):
    return (self.closure,)

class Cast(Expr):
  # inherits the member 'type' from Expr, but for Cast nodes it is mandatory
  _members = ['value']

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

class Alloc(Expr):
  """Allocates a block of data, returns a pointer"""

  _members = ['elt_type', 'count']

  def __str__(self):
    return "alloc<%s>[%s] : %s" % (self.elt_type, self.count, self.type)

  def children(self):
    return (self.count,)

class TypedFn(Expr):
  """
  The body of a TypedFn should contain Expr nodes which have been extended with
  a 'type' attribute
  """

  _members = ['name',
              'arg_names',
              'body',
              'input_types',
              'return_type',
              'type_env',
              # these last two get filled by 
              # transformation/optimizations later 
              'last_transform_by', 
              'version',
              'has_tiles' 
              'num_tiles']
  
  registry = {}
  max_version = {}
  def next_version(self, name):
    n = self.max_version[name] + 1
    self.max_version[name] = n 
    return next 
  
  def node_init(self):
    print self.members()
    assert isinstance(self.body, list), \
        "Invalid body for typed function: %s" % (self.body,)
    assert isinstance(self.arg_names, (list, tuple)), \
        "Invalid typed function arguments: %s" % (self.arg_names,)
    assert isinstance(self.name, str), \
        "Invalid typed function name: %s" % (self.name,)

    if isinstance(self.input_types, list):
      self.input_types = tuple(self.input_types)

    assert isinstance(self.input_types, tuple), \
        "Invalid input types: %s" % (self.input_types,)
    assert isinstance(self.return_type, core_types.Type), \
        "Invalid return type: %s" % (self.return_type,)
    assert isinstance(self.type_env, dict), \
        "Invalid type environment: %s" % (self.type_env,)

    self.type = core_types.make_fn_type(self.input_types, self.return_type)

    if self.version is None:
      self.version = 0 
      self.max_version[self.name] = 0
      
    registry_key = (self.name, self.version) 
    assert registry_key not in self.registry, \
        "Typed function %s version %d already registered" % (self.name, self.version)
    self.registry[registry_key] = self
    
    if self.has_tiles is None:
      self.has_tiles = False
    if self.num_tiles is None:
      self.num_tiles = 0

  def __repr__(self):
    arg_strings = []

    for name in self.arg_names:
      arg_strings.append("%s : %s" % (name, self.type_env.get(name)))

    return "function %s(%s) => %s:%s" % \
           (self.name, ", ".join(arg_strings),
            self.return_type,
            block_to_str(self.body))

  def __str__(self):
    return self.__repr__()

  def __hash__(self):
    return hash(self.name)

  def children(self):
    return ()
