.. _user-documentation:


Installation
=============

Here is a step by step guide on how to install Switchboard. It will help you
download Switchboard and set it up with your application.

Install Switchboard and its the dependencies using ``pip``::

    pip install switchboard

Next we need to bootstrap Switchboard within your application. The best approach
depends on which application framework you're using.

Pyramid
-------

Switchboard has a pyramid add-on available to make pyramid setup easier::

    pip install pyramid_switchboard

Once the dependency is in place, there are several ways to make sure that
``pyramid_switchboard`` is active and Switchboard is up and running. They are
all equivalent.

1. Add ``pyramid_switchboard`` to the ``pyramid.includes`` section of your
   application's main configuration section::

    [app:main]
    ...
    pyramid.includes = pyramid_switchboard

2. Use the ``includeme`` function via `config.include`::

    config.include('pyramid_switchboard')

3. Optionally setup the ``switchboard.template_helpers.is_active`` helper
   function. It can be used with the template engine to make it easier to
   reference switches in the template. For example, if Jinja is being used,
   the following lines in the ``production.ini`` will add the helper as a
   test_::

    jinja2.tests =
        active = switchboard.template_helpers.is_active

   This configuration makes checking switches very easy in Jinja templates::

    {% if 'foo' is active %}
    ... do something ...
    {% else %}
    ... do something else ...
    {% endif %}


Once activated, Switchboard's dashboard is accessible at ``/_switchboard/`` and
switches can now be used in the code.

Other frameworks
----------------

Switchboard is compatible with any application framework that uses WebOb_ as the
underlying request/response library. Even if a plugin/add-on doesn't exist,
Switchboard can still be setup manually.

Configuration
^^^^^^^^^^^^^

The first step is to configure switchboard in your application's config file.
Switchboard has only a handful of settings, none of which are required:

+------------------------------+-------------+--------------------------------+
| Key                          | Default     | Description                    |
+==============================+=============+================================+
| switchboard.mongo_host       | localhost   | The host for MongoDB.          |
+------------------------------+-------------+--------------------------------+
| switchboard.mongo_port       | 27017       | The port for MongoDB.          |
+------------------------------+-------------+--------------------------------+
| switchboard.mongo_db         | switchboard | The database name.             |
+------------------------------+-------------+--------------------------------+
| switchboard.mongo_collection | switches    | The collection name.           |
+------------------------------+-------------+--------------------------------+
| switchboard.internal_ips     |             | Comma-delimited list of IPs.   |
+------------------------------+-------------+--------------------------------+

Note that the "switchboard" prefix for the setting keys is also optional; more
on that in the `Initializing`_ section below.

Initializing
^^^^^^^^^^^^

In the application's bootstrap or initialization code, pass the settings into
Switchboard's ``configure`` method::

    from switchboard import configure
    ...
    configure(settings, nested=True)

If the setting keys are *not* prefixed with "switchboard" you can omit the
``nested=True`` argument.

The dashboard
^^^^^^^^^^^^^

Once Switchboard is configured, you'll need to setup a view that exposes
Switchboard's dashboard.

**Really Important Security Note**: Please configure this view so that only
admins can access it. Switchboard is a powerful tool and should be adequately
secured.

Switchboard uses Mako to render its templates, so the framework may need to be
configured to load the Mako_ engine.

Routing
^^^^^^^

Choose a URL within the application to use as Switchboard's root route; this
will be referred to as ``SWITCHBOARD_ROOT``. Additonal routes underneath
``SWITCHBOARD_ROOT`` will also need to be setup:

* ``SWITCHBOARD_ROOT/``
* ``SWITCHBOARD_ROOT/add``
* ``SWITCHBOARD_ROOT/update``
* ``SWITCHBOARD_ROOT/status``
* ``SWITCHBOARD_ROOT/delete``
* ``SWITCHBOARD_ROOT/add_condition``
* ``SWITCHBOARD_ROOT/remove_condition``
* ``SWITCHBOARD_ROOT/history``

Views
^^^^^

Depending on the framework, a view or controller will need to be created to
handle the routes above. Switchboard includes an example_ of integrating with
`Bobo <http://bobo.digicool.com/en/latest/>`_, a lightweight framework that
uses WebOb_. This class will need to do the following:

* Provide handlers for all of the `Routing`_.
* Define the output (HTML or JSON) for each handler.
* Wrap Switchboard's ``switchboard.admin.controllers.CoreAdminController``.

Implement methods within the view class to handle each of the routes below.
They should delegate to the corresponding function in ``CoreAdminController``
and render the specified output.

+---------------------------------------+--------+-------------------------------------------+
| Route                                 | Output | Template                                  |
+=======================================+========+===========================================+
| ``SWITCHBOARD_ROOT/``                 | HTML   | ``switchboard.admin.templates.index.mak`` |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/add``              | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/update``           | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/status``           | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/delete``           | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/add_condition``    | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/remove_condition`` | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+
| ``SWITCHBOARD_ROOT/history``          | JSON   | NA                                        |
+---------------------------------------+--------+-------------------------------------------+

For more details, please look through the example_ code. Once the views are
defined you should be able to start using switches in your code:

Post-request cleanup
^^^^^^^^^^^^^^^^^^^^

The last thing to setup is to trigger an event when the request is finished.
Switchboard needs to cleanup some caching data; if this event is not triggered,
changes to the switches will not propogate out without server restarts.
Depending on the framework's architecture, invoking something at the end of a
request may mean creating some sort of WSGI middleware, or implementing an
event handler. For example, as WSGI middleware::

    from webob import Request
    from switchboard.signals import request_finished

    class SwitchboardMiddleware(object):

        def __init__(self, app):
            self.app = app

        def __call__(self, environ, start_response):
            req = resp = None
            try:
                req = Request(environ)
                resp = req.get_response(self.app)
                return resp(environ, start_response)
            finally:
                self._end_request(req)

        def _end_request(self, req):
            if req:
                # Notify Switchboard that the request is finished
                request_finished.send(req)


Using switches
==============

Once Switchboard is up and running within the application, it's time to begin
using switches within the code. By default, Switchboard is set to autocreate
switches, which means that a switch just needs to be checked in code and if
it doesn't exist it will be created and disabled by default. A switch is always
referred to by its key, a string name that is expected to be unique to that
key.

In Python
---------

To use in Python code (views, models, etc.), import the operator singleton
and use the ``is_active`` method to see if the switch is on or not::

    from switchboard import operator
    ...
    if operator.is_active('foo'):
        ... do something ...
    else:
        ... do something else ...

If autocreate is on (and it is by default), the 'foo' switch will be
automatically created and set to disabled the first time it is referenced.
Activating the switch and controlling exactly when the switch is active,
are covered in `Managing switches`_.

In templates
------------

Every templating framework has its own take on how (or even if) logic may be
used. That said, Switchboard provides some helpers to make things easier. If

In javascript
-------------

The easiest way to use Switchboard in conjunction with Javascript is to set a
Javascript flag within your template code and then use that flag within your
Javascript logic. Using Mako's syntax in the template::

    <%!
        from switchboard import operator
    %>
    <script>
        window.switches = window.switches || {};
        % if operator.is_active('foo'):
        switches.foo = true;
        % else:
        switches.foo = false;
        % endif
    </script>

In the Javascript::

    if (switches.foo) {
        ... do something ...
    } else {
        ... do something else ...
    }

Again, this time using Jinja syntax and the Switchboard-provided "active"
test_::

    <script>
        window.switches = {};
        switches.foo = {{ 'true' if 'foo' is active else 'false' }};
    </script>

Context objects
---------------

Every switch is evaluated (to see if it is active or not) within a particular
context. By default, that context includes the request object, which allows
Switchboard to specify conditions such as: "make this switch active only for
requests with 'foo' in the query string." That said, there may be other
objects that would be handy to have available in the context. For example, in
an ecommerce setting, the Product model may have a ``new`` flag. By passing
the model into the ``is_active`` method, Switchboard can now activate
switches based on that flag::

    if operator.is_active('foo', my_product):

Any objects passed into the ``is_active`` method after the switch's key will be
added to the context. Normally when dealing with context objects, a custom
condition will be required to actually evaluate the switch against that object.

Custom conditions
-----------------

Switchboard supports custom conditions, allowing application developers to
adapt switches to their particular needs. Creating a condition typically
consists of extending `switchboard.conditions.ConditionSet`.

An example: if the application needs to activate switches for visitors from a
particular country, a custom condition can do the geo lookup on the IP from
the request and return the country value::

    from switchboard.conditions import ConditionSet, Regex
    from my_app.geo import country_code_by_addr

    class GeoConditionSet(ConditionSet):
        countries = Regex()

        def get_namespace(self):
            return 'geo'

        def get_field_value(self, instance, field_name):
            if field_name == 'countries':
                return country_code_by_addr(client_ip())

        def get_group_label(self):
            return 'Geo'

The first thing in the custom condition is to define the fields that makeup the
condition. In this case, there is one "countries" field, which is a regex,
allowing admins to specify criteria like `(US|CA)` (US or Canada). Here are the
fields supported by Switchboard:

* `switchboard.conditions.Boolean` - used for binary, on/off fields
* `switchboard.conditions.Choice` - used for multiple choice dropdowns
* `switchboard.conditions.Range` - used for numeric ranges
* `switchboard.conditions.Percent` - a special type of range specific to
  percentages
* `switchboard.conditions.String` - string matching
* `switchboard.conditions.Regex` - regex expression matching
* `switchboard.conditions.BeforeDate` - before a date
* `switchboard.conditions.OnOrAfterDate` - on or after a date


Managing switches
=================

Switches are managed in the dashboard, which is located at the
`SWITCHBOARD_ROOT` within the application. The dashboard allows:

* Viewing and searching all switches.
* Reviewing or auditing a switch's history.
* Adding, editing, and removing switches.
* Controlling a switch's status.
* Setting up condition sets for a switch.

Of all these capabilities, the last two are of the most interest, as the status
and condition sets determine whether a switch is active.

Statuses
--------

There are four statuses:

* Inactive - disabled for everyone
* Selective - active only for matched conditions
* Inherit - inherit from the parent switch
* Global - active for everyone

Inactive and global are opposite extremes: the switch is turned on or
off for everyone. The inherit status is used for `Parent-child switches`_. The
selective status means that the switch is only active if it passes the
condition sets.

By default, a switch will be created and set to the inactive status. Typical
workflow would be to put code using a switch into production. It will be
autocreated on first reference and thus visible in the dashboard. Once
visible, the admin can set any desired conditions before finally activating the
switch by setting it to the proper status.

Condition Sets
--------------

When a switch is in seletive status, Switchboard checks the
conditions within the condition set to see if the switch should
be active. Conditions are criteria such as "10% of all visitors" or
"only logged in users" that can be applied to the request to see if the
switch should be active. When a switch is in selective status, it will
only be active if it meets the conditions in place.

Parent-child switches
---------------------

Switchboard allows a switch to inherit conditions from a parent, which can be
useful when you want multiple switches to share a common condition set. To
setup parent-child relationship, simply prefix the switch with the parent's
key, using a colon ':' as the separator. You can create parent-child
relationships as deep as you want, e.g., `grandparent:parent:child`.

A real world example: using Switchboard to conduct an AB test. AB tests
have two gates: the first are the visitors who are part of the test, and the
second is to determine who sees which variant. In this example, 10% of site
traffic should be in the test, with half (i.e., 5% of traffic) seeing the normal
(control) A variant and the other half seeing the B variant. The test is setup
with two switches:

* abtest
* abtest:B

The `abtest` switch has a "0-10% of traffic" condition set. The `abtest:B`
switch will inherit from `abtest` and can add its own "0-5% of traffic"
condition. Half of those in the test will see the B variant, the rest will see
the control A variant.

Note that you'll still need an additional tool, like
`Google Analytics Content Experiments`_, to measure conversion within each
variant, but Switchboard can handle traffic segmentation.

Two potential spots of confusion:

1. Child switches *always* inherit from their parents, even when the child
   switch's status is set to something other than inherit. An inherit status
   just means the child switch isn't adding to the parent switch's status.

2. It is also important to note that when a parent switch is disabled, it takes
   precedence over the statuses of any child switches. On the other hand, if the
   parent switch is enabled, it can be overriden by the child switch, e.g., if
   the parent has a global status but the child has an inactive status, the
   child's inactive wins out.


.. _test: http://jinja.pocoo.org/docs/dev/templates/#tests
.. _example: https://github.com/switchboardpy/switchboard/blob/master/example/server.py
.. _WebOb: http://www.webob.org/
.. _Mako: http://makotemplates.org/
.. _`Google Analytics Content Experiments`: https://support.google.com/analytics/answer/1745147?hl=en
