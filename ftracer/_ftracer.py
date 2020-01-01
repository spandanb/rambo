import sys

from .ast_indexer import index_module
from .dynamic_trace import Tracer



def set_trace(target_path, runner_path, cassette_path=None):
    astree = index_module(target_path)
    tracerfun = Tracer(target_path, runner_path, astree=astree, cassette_path=cassette_path)
    return sys.settrace(tracerfun)
