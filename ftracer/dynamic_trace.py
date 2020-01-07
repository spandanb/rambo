'''
contains configurable tracing class
'''
import os
import os.path

from .utils import to_abspath, load_module


class Tracer:
    '''
    implements configurable flow recording
    '''
    def __init__(self, paths, tree_fn, cassette_path=None, step=False,
                 config_path='./config.py'):
        '''
        the tracer will need to track objects seens and events observed.

        Args:
            paths: a list of modules to trace
            tree_fn: callable, given module path returns `NodeIndexer`.
                this enables lazy access
            step: whether to step through execution i.e. prompt
            cassette_path: location where cassette is recorded
            config_path: location of config file (abs or rel)
        '''
        self.paths = paths
        self.tree_fn = tree_fn
        self.step = step
        # config object
        self.config = load_module(to_abspath(config_path))
        self.cassette = self.init_cassette(cassette_path)
        # objects being tracked/viewed and to be serialized
        # we need to track it to avoid duplicate serialization
        self.objects = {}
        # to avoid recording duplicate resolved names
        self.resolved = set()


    def init_cassette(self, cassette_path=None):
        '''
        determine correct cassette path and return
        cassette file descriptor
        '''
        if cassette_path is None:
            cdir = to_abspath(self.config.cassettes_dir)
            cassette_path = os.path.join(cdir, 'A.tape')
        return open(cassette_path, 'w')

    def __call__(self, frame, event, arg):
        return self.tracer(frame, event, arg)

    def __del__(self):
        self.cassette.close()

    def _resolve_name(self, name, frame):
        '''
        resolve name from the frame env vars.
        does not handle non-local variables.
        '''
        if name in frame.f_locals:
            return frame.f_locals[name]
        elif name in frame.f_globals:
            return frame.f_globals[name]
        else:
            raise ValueError(f'Unknown name: {name}')

    def record(self, filepath:str, lineno:int, event:str):
        '''
        record a `event` (currently a string) to file
        '''
        print(f'fpath={filepath} lineno={lineno} event={event}')
        #self.cassette.write(f'{event}\n')

    def tracer(self, frame, event, arg):
        '''
        output variable name and object as it
        traces through a flow.
        '''
        filepath = frame.f_code.co_filename
        # print(filepath)
        if filepath not in self.paths:
            # skip files not matching target/runner module
            return self

        lineno = frame.f_lineno
        self.record(filepath, lineno, event)

        astree = self.tree_fn(filepath)
        if event == 'line' or event == 'return':
            # get names defined in current scope in previous line
            # since the object itself will only be
            # accessible in this call
            # TODO: ensure var is only printed once
            lno_names = astree.prev_lno_names(lineno)
            if (filepath, lno_names.lineno) not in self.resolved:
                for name in lno_names.names:
                    value = self._resolve_name(name, frame)
                    # output the name and the resolved value
                    event = f'Name {name} : {value}'
                    self.record(filepath, lineno, event)

                self.resolved.add((filepath, lno_names.lineno))

        # prompt user to proceed
        # TODO: remove; this is a leftover from when recording
        # and tracing were not separate
        if self.step:
            input('step? ')

        print('-'*40)
        return self
