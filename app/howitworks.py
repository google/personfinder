from model import *
from utils import *


class Howitworks(Handler):
    subdomain_required = False

        
    def get(self):
        return self.render('templates/howitworks.html',
                           text=get_page_text("howItWorks"))

if __name__ == '__main__':
    run(('/howitworks', Howitworks))
