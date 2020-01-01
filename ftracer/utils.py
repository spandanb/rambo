import ast
import os.path
import importlib.util


def read_module(module_path: str) -> str:
    return open(module_path).read()

def module2ast(module_path: str) -> ast.AST:
    with open(module_path) as fp:
        return ast.parse(fp.read())

def realpath(relpath: str) -> str:
    'abs path from relative path'
    return os.path.realpath(relpath)

def with_suffix(fname: str, suffix: str, connector: str='-'):
    '''
    get filename with suffix
    where fname is like  `name.ext`,
    return `name<connector><suffix>.ext`
    '''
    head, tail = os.path.splitext(fname)
    return f'{head}{connector}{suffix}{tail}'


def quoted(s: str):
    'add single quotes around string'
    return f"'{s}'"


def load_module(module_path, module_name='__noname__'):
    '''
    load a module
    '''
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    # load the object
    spec.loader.exec_module(mod)
    return mod


def to_abspath(path, parent=None):
    '''
    convert an rel/abs ambiguous path
    to an absolute path
    '''
    if os.path.isabs(path):
        return path
    parent = parent or os.getcwd()
    return os.path.join(parent, path)


def env_str(env: dict, keys_only=True):
    '''
    Unused- Nuke
    convert a dictionary of env vars to str
    '''
    if keys_only:
        return str(env.keys())
    return str({k: v for k, v in env.items() if k != '__builtins__'})
