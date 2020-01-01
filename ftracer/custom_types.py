'''
custom types primarily used to
create an index on a module

perhaps, this should be combined with classes/types
from ast_indexer.py
'''
from ascii_tree import make_and_print_tree


class UndefinedRelationship(Exception):
    '''
    When two ranges are undefined relationship,
    i.e. overlapping ranges where one is strictly
    not a subset of the other. This exception would
    imply a logic error in misconstructing a tree.
    '''

class EmptyTree(Exception):
    '''
    unable to perform certain op
    '''
    pass


class Stack:
    def __init__(self, items=None):
        if items is None:
            self.stack = []
        elif isinstance(items, list):
            self.stack = items
        else:
            raise ValueError('items arg must be a list')

    @property
    def is_empty(self):
        return len(self.stack) == 0

    def top(self):
        '''raises if stack empty'''
        return self.stack[-1]

    def push(self, val):
        self.stack.append(val)

    def pop(self):
        return self.stack.pop()


class Range:
    '''
    implements a range
    '''
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def encloses(self, other):
        'whether self encloses `other`'
        return self.start <= other.start and self.end >= other.end

    def precedes(self, other):
        return self.end < other.start

    def succeeds(self, other):
        return self.start > other.end

    def __repr__(self):
        return f'Range({self.start}, {self.end})'


class TreeNode:
    def __init__(self, val):
        self.val =  val
        # sorted list of children as (Range, val)
        self.children = []

    @property
    def value(self):
        return self.val

    def add_child(self, key, val, idx):
        self.children.insert(idx, (key, val))

    def __repr__(self):
        return f'TreeNode({self.val})'


class NORangeTree:
    '''
    A N[on]O[verlapping]Range tree specialized for
    tracking scopes. Scopes can have children
    scopes and have an associated range of lineno.

    Requires:
        1) non-overlapping ranges
        2) parent ranges are added before child ranges
           NOTE: could be updated to handle out of order
           updates, but unneeded as yet.
        3) Children scopes are subsets of parents (not
            necessarily proper subset)

    NOTE: currently `TreeNode` is dumb and `RangeTree`
    contains all the logic- sometimes reading
    TreeNode internals.
    '''
    def __init__(self):
        self.root = TreeNode(None)

    def _add_node(self, ancestor: TreeNode, key: Range, node: TreeNode):
        '''
        Add a new node. `node` has `key` and may
        be child of `ancestor`
        of it may be a deeper descendent.
        If there is an existing child node(s) in this range
        we recurse to find the correct parent.
        Else, add it as a child of `ancestor`.
        NB: this expect parents to be added before children
        '''
        left = 0
        right = len(ancestor.children) - 1
        idx = 0
        while left <= right:
            mid = (left + right) // 2
            ch_key, ch_node = ancestor.children[mid]
            # there are 3 possible states that ch_key and key
            # can be in: encloses, precedes, or succeeds
            if ch_key.encloses(key):
                return self._add_node(ch_node, key, node)
            elif ch_key.precedes(key):
                # ch_key is before key; look to the right of mid
                # but if this is the last idx before we terminate
                # then that must be the index of insertion
                left = mid + 1
                idx = mid + 1
            elif ch_key.succeeds(key):
                right = mid - 1
                idx = mid - 1
            else:
                # overlapping range; misconstructed tree
                # or out of order insertion, i.e. bigger scope
                # after an enclosing scope
                raise UndefinedRelationship

        return ancestor.add_child(key, node, idx)

    def add_node(self, start_key: int, end_key: int, val):
        '''
        Add a new node.
        '''
        key = Range(start_key, end_key)
        new_node = TreeNode(val)
        self._add_node(self.root, key, new_node)

    def get_scope_stack(self, lineno: int):
        '''
        Get the scope(s) at a specific `lineno`
        '''
        if not self.root.children:
            # tree is empty- can't search
            raise EmptyTree

        node = self.root
        left = 0
        right = len(node.children) - 1
        # to simplify ops
        lno_range = Range(lineno, lineno)
        result = []
        while left <= right:
            mid = (left + right) // 2
            ch_key, ch_node = node.children[mid]
            # there are 3 possible states that ch_key and key
            # can be in: encloses, precedes, or succeeds
            if ch_key.encloses(lno_range):
                # update result and loop over a smaller range
                node = ch_node
                left = 0
                right = len(node.children) - 1
                result.append(node)
            elif ch_key.precedes(lno_range):
                # ch_key is before key; look to the right of mid
                left = mid + 1
            elif ch_key.succeeds(lno_range):
                right = mid - 1
            else:
                break

        return Stack(result)


def get_children(n):
    return [v for k, v in n.children]


if __name__ == '__main__':
    rtree = NORangeTree()
    rtree.add_node(1, 10, 'global')
    rtree.add_node(1, 3, 'funcfoo')
    rtree.add_node(4, 4, 'funcbar')
    # make_and_print_tree(rtree.root, get_val=lambda n: n.val, get_children=get_children)
    # print(rtree.get_scope_stack(4))
    import pickle
    print(len(pickle.dumps(rtree)))
