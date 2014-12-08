import pkg_resources

import bobo
from mako.template import Template

from switchboard import operator, configure
from switchboard.admin.controllers import CoreAdminController

configure()


@bobo.query('/')
def index():
    if operator.is_active('example'):
        return 'The example switch is active.'
    else:
        return 'The example switch is NOT active.'


@bobo.subroute
def admin(request):
    return AdminController()


@bobo.scan_class
class AdminController:
    def __init__(self):
        self.c = CoreAdminController()

    @bobo.resource('')
    def base(self, bobo_request):
        return bobo.redirect(bobo_request.url + '/')

    @bobo.query('/')
    def index(self, by='-date_modified'):
        path = pkg_resources.resource_filename('switchboard.admin.templates',
                                               'index.mak')
        with open(path, 'r') as f:
            tmpl = f.read()
        data = self.c.index(by)
        html = Template(tmpl).render(**data)
        return html

    @bobo.post('/add', content_type='application/json')
    def add(self, key, label='', description=None, **kwargs):
        return self.c.add(key, label, description, **kwargs)

    @bobo.post('/update', content_type='application/json')
    def update(self, curkey, key, label='', description=None):
        return self.c.update(curkey, key, label, description)

    @bobo.post('/status', content_type='application/json')
    def status(self, key, status):
        return self.c.status(key, status)

    @bobo.post('/delete', content_type='application/json')
    def delete(self, key):
        return self.c.delete(key)

    @bobo.post('/add_condition', content_type='application/json')
    def add_condition(self, bobo_request):
        return self.c.add_condition(**bobo_request.POST)

    @bobo.post('/remove_condition', content_type='application/json')
    def remove_condition(self, bobo_request):
        return self.c.remove_condition(**bobo_request.POST)

    @bobo.query('/history', content_type='application/json')
    def history(self, key):
        return self.c.history(key)
