from google.appengine.api import datastore_errors

from model import *
from utils import *


class Page(Handler):
    subdomain_required = False
            
    def get(self, name):
        return self.render('templates/page.html',
                           text=model.Page.get(name,self.env.lang))

if __name__ == '__main__':
    run(('/page/(.*)', Page))
