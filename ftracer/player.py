'''
API for playing the cassette
'''
from . import tape_utils as tu


class TapePlayer:
    '''
    Play a flow cassette.
    Interface broadly resembles pdb.
    '''
    def __init__(self, cassette_path, step=True):
        '''
        step: whether to step through execution i.e. prompt
        '''
        self.cassette = tu.get_records(cassette_path)
        self.step = step

    def play(self):
        '''
        step through cassette
        '''
        for record in self.cassette:
            print(record)
            # prompt user to step
            if self.step:
                input('step? ')

        print('finished')
