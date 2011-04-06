from mapreduce.operation.counters import Increment
from mapreduce.operation.db import Put

def make_prefixed_increment(prefix):
    return lambda name: Increment(prefix + '.' + name)

def count_person(person):
    inc = make_prefixed_increment(person.subdomain + '.person')
    yield inc('all')
    yield inc('original_domain=' + (person.original_domain or ''))
    yield inc('sex=' + (person.sex or ''))
    yield inc('home_country=' + (person.home_country or ''))
    yield inc('photo=' + (person.photo_url and 'present' or ''))
    yield inc('num_notes=%d' % len(person.get_notes()))
    yield inc('status=' + (person.latest_status or ''))
    yield inc('found=' + repr(person.latest_found))
    yield inc('linked_persons=%d' % len(person.get_linked_persons()))

def count_note(note):
    inc = make_prefixed_increment(person.subdomain + '.note')
    yield inc('all')
    yield inc('original_domain=' + (note.original_domain or ''))
    yield inc('status=' + (note.status or ''))
    yield inc('found=' + repr(note.found))
    if note.linked_person_record_id:
        yield inc('linked_person')
    if note.last_known_location:
        yield inc('last_known_location')

def add_property(entity):
    """If the specified property is not present, set it to its default value."""
    params = context.get().mapreduce_spec.mapper.params
    name = params['property_name']
    if getattr(entity, name, None) is None:
        setattr(entity, name, entity.properties()[name].default_value())
        yield Put(entity)
