from mapreduce.operation.counters import Increment
from mapreduce.operation.db import Put

BOOLEANS = {True: 'TRUE', False: 'FALSE', None: ''}

def count_person(person):
    yield Increment('person.all')
    yield Increment('person.original_domain=' + (person.original_domain or ''))
    yield Increment('person.sex=' + (person.sex or ''))
    yield Increment('person.home_country=' + (person.home_country or ''))
    yield Increment('person.photo=' + (person.photo_url and 'present' or ''))
    yield Increment('person.num_notes=%d' % len(person.get_notes()))
    yield Increment('person.status=' + (person.latest_status or ''))
    yield Increment('person.found=' + BOOLEANS.get(person.latest_found, ''))
    yield Increment('person.linked_persons=%d' %
                    len(person.get_linked_persons()))

def count_note(note):
    yield Increment('note.all')
    yield Increment('note.original_domain=' + (note.original_domain or ''))
    yield Increment('note.status=' + (note.status or ''))
    yield Increment('note.found=' + BOOLEANS.get(note.found, ''))
    if note.linked_person_record_id:
        yield Increment('note.linked_person')
    if note.last_known_location:
        yield Increment('note.last_known_location')

def add_boolean_property(entity):
    params = context.get().mapreduce_spec.mapper.params
    name = params['property_name']
    if not getattr(entity, name):
        setattr(entity, name, False)
        yield Put(entity)
