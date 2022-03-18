from __future__ import unicode_literals
from __future__ import absolute_import

import os

from bottle import Bottle, redirect, run

from switchboard import operator, configure
from switchboard.middleware import SwitchboardMiddleware
from switchboard.admin import app as switchboard

configure({'mongo_timeout': 1000},
          allow_no_mongo=not os.environ.get('MUST_USE_REAL_MONGO'),
          )

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

run(app, host='localhost', port=8080, debug=True,
    reloader=False)
