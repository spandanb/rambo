import sys

from functools import lru_cache
from .ast_indexer import index_module
from .dynamic_trace import Tracer


def set_trace(target_path, runner_path, cassette_path=None):
    tree_fn = lru_cache(index_module)
    tracerfun = Tracer([target_path, runner_path], tree_fn, cassette_path=cassette_path)
    return sys.settrace(tracerfun)
