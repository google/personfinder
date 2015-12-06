import logging
import model
from google.appengine.ext import deferred
from google.appengine.ext import db

BATCH_SIZE = 100  # ideal batch size may vary based on entity size.

def UpdateSchema(cursor=None, num_updated=0):
    query = model.Person.all_in_repo('chennai')
    if cursor:
        query.with_cursor(cursor)
    to_put = []
    for p in query.fetch(limit=BATCH_SIZE):
        # In this example, the default values of 0 for num_votes and avg_rating
        # are acceptable, so we don't need this loop.  If we wanted to manually
        # manipulate property values, it might go something like this:
        p.role = 'seek'
        to_put.append(p)

    if to_put:
        db.put(to_put)
        num_updated += len(to_put)
        logging.info(
            'Put %d entities to Datastore for a total of %d',
            len(to_put), num_updated)
        deferred.defer(
            UpdateSchema, cursor=query.cursor(), num_updated=num_updated)
    else:
        logging.info(
            'UpdateSchema complete with %d updates!', num_updated)
