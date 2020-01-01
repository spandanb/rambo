'''
contains configurable tracing class
'''
import os
import os.path

from .utils import to_abspath, load_module


class Tracer:
    '''
    class to implement configurable tracing
    '''
    def __init__(self, target_path, runner_path, astree=None, cassette_path=None, step=False,
                 config_path='./config.py'):
        '''
        There needs to be a better understanding of the
        relationship b/w target and run_path. In some cases,
        the runner may only be responsible for triggering the
        flow, but in other cases it might be integral to the flow,
        e.g. creates objects etc.

        Args:
            target_path: the module to trace
            runner_path: the module that triggers the flow.
            step: whether to step through execution i.e. prompt
            asttree: ast module node for module being analyzed
            cassette_path: location where cassette is recorded
            config_path: location of config file (abs or rel)
        '''
        self.target_path = target_path
        self.runner_path = runner_path
        self.step = step
        self.astree = astree

        self.config = load_module(to_abspath(config_path))
        self.cassette = self.init_cassette(cassette_path)

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

    def record(self, frame):
        '''
        record a `frame` to file
        '''
        self.cassette.write(f'{frame}\n')

    def tracer(self, frame, event, arg):
        '''
        output variable name and object as it
        traces through a flow.
        '''
        filepath = frame.f_code.co_filename
        # print(filepath)
        if filepath != self.target_path and filepath != self.runner_path:
            # skip files not matching target/runner module
            return self

        lineno = frame.f_lineno
        desc = f'fpath={filepath} lineno={lineno} event={event}'
        print(desc)
        self.record(desc)

        if event == 'line':
            # get names defined in current scope in previous line
            # since the object itself will only be
            # accessible in this call
            names = self.astree.prev_unresolved(lineno)
            for name in names:
                resolved = self._resolve_name(name, frame)
                # output the name and the resolved variable
                print(f'Var {name} : {resolved}')

        # prompt user to proceed
        if self.step:
            input('step? ')

        print('-'*40)
        return self
