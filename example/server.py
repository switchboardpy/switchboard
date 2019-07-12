from __future__ import unicode_literals
from __future__ import absolute_import
import pickle

from bottle import Bottle, redirect, run
import datastore.core

from switchboard import operator, configure
from switchboard.middleware import SwitchboardMiddleware
from switchboard.admin import app as switchboard


# Setup a file-based datastore with pickle serialization.
import datastore.filesystem
import os
base_path = os.path.dirname(os.path.realpath(__file__))
ds_file = os.path.join(base_path, '.switches')
ds_child = datastore.filesystem.FileSystemDatastore(ds_file)
ds = datastore.serialize.shim(ds_child, pickle)

# Configure Switchboard.
configure(datastore=ds)

# Fire up the example application.
app = Bottle()
app.mount('/_switchboard/', switchboard)


@app.get('/')
def index():
    if operator.is_active('example'):
        return 'The example switch is active.'
    else:
        return 'The example switch is NOT active.'


@app.get('/_switchboard')
def trailing_slash():
    redirect('/_switchboard/')


app = SwitchboardMiddleware(app)


run(app, host='localhost', port=8080, debug=True, server='paste',
    reloader=True)
