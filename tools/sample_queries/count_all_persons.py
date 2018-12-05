# Sample query for counting all the Person entries between dates.
from __future__ import print_function
import datetime

query = Person.all(filter_expired=False).filter(
    'entry_date >=', datetime.datetime(2013, 1, 1, 0, 0, 0)).filter(
    'entry_date <', datetime.datetime(2014, 1, 1, 0, 0, 0))
count = 0
while True:
    current_count = query.count()
    if current_count == 0:
        break
    count += current_count
    query.with_cursor(query.cursor())
print('# of persons =', count)
