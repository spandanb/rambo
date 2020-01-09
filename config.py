'''
python module as config file
providing relevant config params as globals names
'''

# rel or abs path to cassettes dir
cassettes_dir = './cassettes'


if __name__ == '__main__':
    # do any init
    import os
    import os.path
    # make cassettes_dir
    if not os.path.isdir(cassettes_dir):
        os.mkdir(cassettes_dir)
