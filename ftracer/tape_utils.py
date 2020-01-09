'''
utils for interacting with avro files
'''
import dill
import functools
from fastavro import writer, reader, parse_schema


'''
the different events are:
    obj_created: a new object was created
    name_assigned: a name was (re)set;
        this is not very useful if tracking object evolution.
        but in general the different events show different
        things about what's happening at runtime.
        a line may include both obj_created and name_assigned
        but the obj_created happens first
    attr_assigned: an object's attribute was (re)set
'''

schema = [
{
    'name': 'event_enum',
    'type': 'enum',
    'symbols': ['OBJECT_CREATED', 'NAME_ASSIGNED', 'ATTR_ASSIGNED']
},
{
    'name': 'object_created',
    'doc': 'object creation event',
    'type': 'record',
    'fields': [
        {'name': 'object', 'type': 'bytes'},
    ]
},
{
    'name': 'event',
    'doc': 'the event that happened',
    'type': 'record',
    'fields': [
        {'name': 'module_path', 'type': 'string'},
        {'name': 'module_lno', 'type': 'int'},
        {'name': 'event_type', 'type': 'event_enum'},
        {'name': 'event_data', 'type': ['object_created']}
    ]
}]

EVENT_SCHEMA = parse_schema(schema)

class Event:
    '''abstract base class representing
    events to record. this is provided
    to facilitate writing to avro
    '''
    def to_dict(self):
        'serialized representation based on schema'
        raise NotImplementedError

class ObjectCreated(Event):
    def __init__(self, object):
        self.object = object

    def to_dict(self):
        return {'object': dill.dumps(self.object)}


@functools.lru_cache
def to_symbol(name):
    '''convert name from pascal to upper snake case,
       e.g. FooBar to FOO_BAR'''
    result = []
    for i, c in enumerate(name):
        if i == 0:
            result.append(c)
        elif c.isupper():
            result.append('_')
            result.append(c)
        else:
            result.append(c.upper())
    return ''.join(result)


def append_record(fileptr, path: str, lineno: int, event: Event):
    '''
    append record to `fileptr`
    '''
    record = {'module_path': path,
              'module_lno': lineno,
              'event_type': to_symbol(event.__class__.__name__),
              'event_data': event.to_dict()}
    writer(fileptr, EVENT_SCHEMA, [record])


def get_records(filepath):
    '''
    generate records in `filepath`
    '''
    with open(filepath, 'rb') as fo:
        for record in reader(fo):
            yield record


if __name__ == '__main__':
    # sanity check
    records = [{'module_path': '', 'module_lno': 0, 'event_type': 'OBJECT_CREATED', 'event_data': {'object': b''}}]
    with open('foo.avro', 'wb') as out:
        writer(out, EVENT_SCHEMA, records)

    # Reading
    with open('foo.avro', 'rb') as fo:
        for record in reader(fo):
            print(record)
