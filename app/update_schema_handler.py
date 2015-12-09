import webapp2
import update_schema
from google.appengine.ext import deferred

class UpdateHandler(webapp2.RequestHandler):
    def get(self):
        deferred.defer(update_schema.UpdateSchema)
        self.response.out.write('Schema migration successfully initiated.')

app = webapp2.WSGIApplication([('/update_schema', UpdateHandler)])
