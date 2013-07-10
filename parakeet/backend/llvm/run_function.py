import ctypes
from llvm.ee import GenericValue

import config
import core_types
import llvm_backend
import llvm_types
import stride_specialization
import syntax
import type_conv
import type_inference

from args import ActualArgs
from llvm_context import global_context
from pipeline import lowering 

def python_to_generic_value(x, t):
  if isinstance(t, core_types.FloatT):
    llvm_t = llvm_types.llvm_value_type(t)
    return GenericValue.real(llvm_t, x)
  elif isinstance(t, core_types.SignedT):
    llvm_t = llvm_types.llvm_value_type(t)
    return GenericValue.int_signed(llvm_t, x)
  elif isinstance(t, core_types.IntT):
    llvm_t = llvm_types.llvm_value_type(t)
    return GenericValue.int(llvm_t, x)
  elif isinstance(t, core_types.PtrT):
    return GenericValue.pointer(x)
  else:
    ctypes_obj = type_conv.from_python(x)
    return GenericValue.pointer(ctypes.addressof(ctypes_obj))

def ctypes_to_generic_value(cval, t):
  if isinstance(t, core_types.FloatT):
    llvm_t = llvm_types.llvm_value_type(t)
    return GenericValue.real(llvm_t, cval.value)
  elif isinstance(t, core_types.SignedT):
    llvm_t = llvm_types.llvm_value_type(t)
    return GenericValue.int_signed(llvm_t, cval.value)
  elif isinstance(t, core_types.IntT):
    llvm_t = llvm_types.llvm_value_type(t)
    return GenericValue.int(llvm_t, cval.value)
  elif isinstance(t, core_types.NoneT):
    return GenericValue.int(llvm_types.int64_t, 0)
  elif isinstance(t, core_types.PtrT):
    return GenericValue.pointer(ctypes.addressof(cval.contents))
  else:
    return GenericValue.pointer(ctypes.addressof(cval))

def generic_value_to_python(gv, t):
  if isinstance(t, core_types.SignedT):
    return t.dtype.type(gv.as_int_signed() )
  elif isinstance(t, core_types.IntT):
    return t.dtype.type( gv.as_int() )
  elif isinstance(t, core_types.FloatT):
    llvm_t = llvm_types.ctypes_scalar_to_lltype(t.ctypes_repr)
    return t.dtype.type(gv.as_real(llvm_t))
  elif isinstance(t, core_types.NoneT):
    return None
  else:
    addr = gv.as_pointer()
    struct = t.ctypes_repr.from_address(addr)
    return t.to_python(struct)

class CompiledFn:
  def __init__(self, llvm_fn, parakeet_fn,
               exec_engine = global_context.exec_engine):
    self.llvm_fn = llvm_fn
    self.parakeet_fn = parakeet_fn
    self.exec_engine = exec_engine

  def __call__(self, *args):
    actual_types = tuple(map(type_conv.typeof, args))
    expected_types = self.parakeet_fn.input_types
    assert actual_types == expected_types, \
        "Arg type mismatch, expected %s but got %s" % \
        (expected_types, actual_types)
    # calling conventions are that output must be preallocated by the caller'
    ctypes_inputs = [t.from_python(v) for (v,t) in zip(args, expected_types)]
    gv_inputs = [ctypes_to_generic_value(cv, t) for (cv,t) in
                 zip(ctypes_inputs, expected_types)]

    gv_return = self.exec_engine.run_function(self.llvm_fn, gv_inputs)
    return generic_value_to_python(gv_return, self.parakeet_fn.return_type)
