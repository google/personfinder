from google.appengine.api import datastore_errors

from model import *
from utils import *


class Howitworks(Handler):
    subdomain_required = False
    
        
    def get(self):
        try:
            text=get_page_text('hiw:'+ self.env.lang)
        except datastore_erros.NeedIndexError:
            text=get_page_text('hiw:en')      

        return self.render('templates/howitworks.html',
                           text=text)

if __name__ == '__main__':
    run(('/howitworks', Howitworks))
