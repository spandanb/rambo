'''
logic to walk and index a module ast.
the index is a forest of scopes, each containing
their child variables
'''
import ast
import functools

from collections import namedtuple
from sortedcontainers import SortedList
from .custom_types import NORangeTree, Stack
from .utils import realpath


class WNode:
    '''
    W(rapper) node
    '''
    def __init__(self, name, astnode):
        self.name = name
        self.astnode = astnode

    def __str__(self):
        return self.name

    def __repr__(self):
        classname = self.__class__.__name__
        return f'{classname}({self.name})'


class RVNode(WNode):
    '''
    A node representing a
    [R]esolvable [V]alue, e.g. a
    class name that resolves to the
    class definition

    NB: This is currently unused; since
    I am not storing- but merely printing
    the resolved value
    '''
    def __init__(self, name, astnode, value=None):
        super().__init__(name, astnode)
        self.value = None


class NameLinenoPair:
    # TODO: remove; why isn't a namedtuple sufficient here
    def __init__(self, lineno, name):
        self.lineno = lineno
        self.name = name

    def __eq__(self, other):
        return self.lineno == other.lineno and self.name == other.name

    @functools.total_ordering
    def __lt__(self, other):
        if self.lineno < other.lineno:
            return True
        elif self.lineno > other.lineno:
            return False
        else:
            return self.name < other.name

    def __str__(self):
        return f'NL({self.lineno}, {self.name})'

    def __repr__(self):
        return self.__str__()


# result type when resolving names in previous line
LinenoNames = namedtuple('LinenoNames', 'lineno names')


class LSNode(WNode):
    '''
    [L]exical[S]scope node.
    Use for node representing a lexical scoping
    entity, e.g. functions, classes.
    '''
    def __init__(self, name, astnode: ast.AST):
        super().__init__(name, astnode)
        self.lhs_children = {}
        self.rhs_children = {}
        # structure for looking up names on previous line
        # currently assuming names only occur on LHS
        # albeit they can appear on either side
        self.lno_idx = SortedList()

    def add_lhs_child(self, childname, child, lineno=None):
        self.lhs_children[childname] = child
        if lineno is not None:
            self.lno_idx.add(NameLinenoPair(lineno, childname))

    def add_rhs_child(self, childname, child):
        self.rhs_children[childname] = child

    def prev_lno_names(self, lineno) -> LinenoNames:
        '''
        find all names in the last line
        before `lineno`

        Would this be better solved with a node
        iterator/more cohesive redesign of
        the classes/interfaces?
        is this question even well defined with
        the current approach of recording
        '''
        name_idx = self.lno_idx.bisect_left(NameLinenoPair(lineno, '')) - 1
        if name_idx < 0:
            return LinenoNames(-1, [])
        # get all vars on queried lno
        query_lno = self.lno_idx[name_idx].lineno
        names = []
        while name_idx >= 0:
            name = self.lno_idx[name_idx].name
            names.append(name)
            # look left
            name_idx -= 1
            # break if we are out of the array or at a previous lineno
            if name_idx < 0 or self.lno_idx[name_idx].lineno != query_lno:
                break

        return LinenoNames(query_lno, names)


class NodeIndexer(ast.NodeVisitor):
    '''
    Walks some source code and creates
    indices on the code.

    TODO: Rename to AstIndexer
    NB: code has to be analyzed in same way
    as python interpreter, i.e. read global definitions first
    then evaluate substructure.
    '''
    def __init__(self):
        # `scope_stack` is a stack of nodes with an implied scope
        # used while actually walking the ast
        self.scope_stack = Stack()
        # `scope_range` structure is a
        # static map from lineno to scope stack
        self.scope_range = NORangeTree()
        # TODO: allow searching for a name?
        super().__init__()

    def prev_lno_names(self, lineno)->LinenoNames:
        '''
        get all var names referenced in the last line
        before lineno.

        NOTE: this doesn't distinguish between
              (un)/resolved variables
        '''
        scopes = self.scope_range.get_scope_stack(lineno)
        # containing scope (LSNode)
        cont_scope = scopes.top().value
        return cont_scope.prev_lno_names(lineno)

    def push_scope(self, name:str, node: LSNode):
        '''
        entities that create a scope, e.g.
        functions, need to
        pushed onto the scope stack
        '''
        self.scope_stack.push(node)
        self.generic_visit(node.astnode)
        self.scope_stack.pop()

    def add_lhs_child(self, name:str, node: LSNode, lineno: int=None):
        '''
        a statement/expression that broadly
        creates a name within a scope
        this assignment may be (im)pure depending
        on whether the variable has previously
        been set.
        '''
        parent = self.scope_stack.top()
        parent.add_lhs_child(name, node, lineno)

    def add_rhs_child(self, name: str, node):
        '''
        a value object. Here we can track function
        invocation, class instantiations, module
        accesses etc.
        with the exception of reassignment, all
        impure operations happen on the rhs
        '''
        raise NotImplementedError()

    def generic_visit(self, node):
        # src: https://github.com/python/cpython/blob/master/Lib/ast.py#L385
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(node, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def visit_Import(self, node):
        for child in ast.iter_child_nodes(node):
            name = child.asname or child.name
            wnode = WNode(name, node)
            # import creates a new name, i.e. like a lhs entity
            self.add_lhs_child(name, wnode)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # TODO: factor out commonalities from visit_{FunctionDef,
        # AsyncFunctionDef, ClassDef} into a helper
        name = node.name
        lsnode = LSNode(name, node)
        self.scope_range.add_node(node.lineno, node.end_lineno, lsnode)
        # add node to current scope
        self.add_lhs_child(name, lsnode)
        # create a current node scope
        scope_name = f'FunctionDef_{name}'
        self.push_scope(scope_name, lsnode)

    def visit_AsyncFunctionDef(self, node):
        name = node.name
        lsnode = LSNode(name, node)
        self.scope_range.add_node(node.lineno, node.end_lineno, lsnode)
        self.add_lhs_child(name, lsnode)
        scope_name = f'AsyncFunctionDef_{name}'
        self.push_scope(scope_name, lsnode)

    def visit_ClassDef(self, node):
        '''
        every specific node visit has to update the time
        varying scope stack and the static scope range
        '''
        name = node.name
        lsnode = LSNode(name, node)
        self.scope_range.add_node(node.lineno, node.end_lineno, lsnode)
        self.add_lhs_child(name, lsnode)
        scope_name = f'ClassDef_{name}'
        self.push_scope(scope_name, lsnode)

    def visit_Module(self, node):
        '''
        first visited node
        '''
        # TODO: name and scope name should be consistent
        name = f'Module_{node.__module__}'
        lsnode = LSNode(name, node)
        start = node.body[0].lineno
        end = node.body[-1].end_lineno
        self.scope_range.add_node(start, end, lsnode)
        self.push_scope(name, lsnode)

    def visit_Assign(self, node):
        '''
        I can just look at the  names being
        updated then in the frame.{locals|globals}
        get the actual value.
        '''
        # not sure where there are multiple targets
        for target in node.targets:
            # target may be a tuple of names
            for part_target in self._unwrap(target):
                tname = self._resolve_name(part_target)
                tnode = WNode(tname, part_target)
                # should this use a RVNode instead
                self.add_lhs_child(tname, tnode, node.lineno)
                # what about the value
                # get the value from the runtime code object
                # TODO: we should still do analysis
                # of right hand side; here it's easier to
                # distinguish (re)assignment vs. passing something
                # around.
        self.generic_visit(node)

    def _resolve_name(self, node):
        '''
        extract name from node
        '''
        if isinstance(node, ast.Attribute):
            # TODO: is this case even triggered
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        else:
            raise ValueError(f'cannot resolve type: {type(node)}')
        return name

    def _unwrap(self, node):
        '''
        if node is a collection, e.g. list, set, or tuple
        return items, else return node
        '''
        if type(node) in (ast.Tuple, ast.List, ast.Set):
            return node.elts
        return [node]


def index_module(module_path:str)->NodeIndexer:
    '''
    walk and index a module at `module_path`
    and return the generated `NodeIndexer`
    '''
    with open(module_path) as fp:
        node = ast.parse(fp.read())
    indexer = NodeIndexer()
    indexer.visit(node)
    return indexer


if __name__ == '__main__':
    indexer = index_module(realpath('./repos/foo/bar.py'))
    # print(indexer.prev_unresolved(7))
