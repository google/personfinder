from mapreduce.operation.counters import Increment
from mapreduce.operation.db import Put

def make_prefixed_increment(prefix):
    return lambda name: Increment(prefix + '.' + name)

def count_person(person):
    """Gathers statistics on a Person entity."""
    inc = make_prefixed_increment(person.subdomain + '.person')
    yield inc('all')
    yield inc('is_expired=' + repr(person.is_expired))
    if not person.is_expired:
        yield inc('expired=False')
        yield inc('original_domain=' + (person.original_domain or ''))
        yield inc('sex=' + (person.sex or ''))
        yield inc('home_country=' + (person.home_country or ''))
        yield inc('photo=' + (person.photo_url and 'present' or ''))
        yield inc('num_notes=%d' % len(person.get_notes()))
        yield inc('status=' + (person.latest_status or ''))
        yield inc('found=' + repr(person.latest_found))
        yield inc('linked_persons=%d' % len(person.get_linked_persons()))

def count_note(note):
    """Gathers statistics on a Note entity."""
    inc = make_prefixed_increment(note.subdomain + '.note')
    yield inc('all')
    yield inc('is_expired=' + repr(note.is_expired))
    if not note.is_expired:
        yield inc('not_expired')
        yield inc('original_domain=' + (note.original_domain or ''))
        yield inc('status=' + (note.status or ''))
        yield inc('found=' + repr(note.found))
        if note.linked_person_record_id:
            yield inc('linked_person')
        if note.last_known_location:
            yield inc('last_known_location')

def rewrite_entity(entity):
    """Writes back the entity as is.  This updates auto_now properties and
    fills in any missing properties with their default values."""
    yield Put(entity)
