import pkg_resources

from bottle import Bottle, redirect, request, run
from mako.template import Template

from switchboard import operator, configure
from switchboard.admin.controllers import CoreAdminController

configure(request=request)
sb = Bottle()
sb.c = CoreAdminController()


@sb.get('/')
def sb_index():
    by = request.query.by or '-date_modified'
    path = pkg_resources.resource_filename('switchboard.admin.templates',
                                           'index.mak')
    with open(path, 'r') as f:
        tmpl = f.read()
    data = sb.c.index(by)
    html = Template(tmpl).render(**data)
    return html


@sb.post('/add')
def sb_add():
    key = request.forms['key']
    label = request.forms.get('label', '')
    description = request.forms.get('description')
    return sb.c.add(key, label, description)


@sb.post('/update')
def sb_update():
    curkey = request.forms['curkey']
    key = request.forms['key']
    label = request.forms.get('label', '')
    description = request.forms.get('description')
    return sb.c.update(curkey, key, label, description)


@sb.post('/status')
def sb_status():
    key = request.forms['key']
    status = request.forms['status']
    return sb.c.status(key, status)


@sb.post('/delete')
def sb_delete():
    return sb.c.delete(request.forms['key'])


@sb.post('/add_condition')
def sb_add_condition():
    return sb.c.add_condition(**request.POST)


@sb.post('/remove_condition')
def sb_remove_condition():
    return sb.c.remove_condition(**request.POST)


@sb.get('/history')
def sb_history():
    return sb.c.history(request.query.key)


app = Bottle()
# NOTE: When switchboard becomes a wrappable WSGI app, the Bottle above can go
# away and we can just mount it directly.
app.mount('/_switchboard/', sb)


@app.get('/')
def index():
    if operator.is_active('example'):
        return 'The example switch is active.'
    else:
        return 'The example switch is NOT active.'


@app.get('/_switchboard')
def trailing_slash():
    redirect('/_switchboard/')


run(app, host='localhost', port=8080, debug=True, server='paste')
