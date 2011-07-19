from google.appengine.api import datastore_errors

from model import *
from utils import *


class Page(Handler):
    subdomain_required = False
            
    def get(self, name):
        try:
            text=get_page_text(name+ ":" +self.env.lang)
        except datastore_errors.NeedIndexError:
            text=get_page_text(name+':en')      
        
        
        return self.render('templates/page.html',
                           text=text)

if __name__ == '__main__':
    run(('/page/(.*)', Page))
