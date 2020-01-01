'''
update module
'''
import ast
import astor

from .utils import module2ast, with_suffix, quoted


class TracingInjector(ast.NodeTransformer):
    '''
    injects tracing code into module
    '''
    def __init__(self, target_mpath, run_mpath):
        '''
        Args:
            target_mpath: abs path of module to be analyzed
            run_mpath: module triggering the flow
        '''
        self.target_mpath = target_mpath
        self.run_mpath = run_mpath
        super().__init__()

    def visit_Module(self, node):
        '''
        Inject tracing logic on top module
        '''
        self.generic_visit(node)
        # list of statements/expr to be prepended to body
        prebody = []
        # "import ftracer"
        line = ast.Import([ast.alias('ftracer', None)])
        prebody.append(line)
        # ftrace.set_trace
        attr = ast.Attribute(ast.Name('ftracer'), 'set_trace', ast.Load())
        # ftrace.set_trace(<target>,<run>)
        call = ast.Call(func=attr,
                        args=[ast.Name(quoted(self.target_mpath)),
                                ast.Name(quoted(self.run_mpath))],
                        keywords=[])
        # ftrace.set_trace(...)
        line = ast.Expr(call)
        prebody.append(line)

        node.body = prebody + node.body
        ast.fix_missing_locations(node)
        return node


def rewrite_module(running_mpath: str, target_mpath: str, suffix: str='instrum'):
    '''
    Rewrite the module (python file) file
    with instrumentation code

    TODO: change all `mpath`s to `path`s

    Args:
        running_mpath: path of module that will be rewritten and run
        target_mpath: path of module to analyze
        suffix: rewrite foo.py as foo-<suffix>.py
    Returns:
        str (path to updated file)
    '''
    # update the runnner
    module = module2ast(running_mpath)
    # updated module path
    new_mpath = with_suffix(running_mpath, suffix)
    # module object updated in-place
    TracingInjector(target_mpath, new_mpath).visit(module)
    # write modified module
    with open(new_mpath, 'w') as fp:
        fp.write(astor.to_source(module))

    return new_mpath
