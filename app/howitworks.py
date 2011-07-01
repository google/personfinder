from utils import *

class Howitworks(Handler):
    subdomain_required = False

    def get(self):

        return self.render('templates/howitworks.html')

if __name__ == '__main__':
    run(('/howitworks', Howitworks))
