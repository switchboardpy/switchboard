.. image:: https://travis-ci.org/switchboardpy/switchboard.svg?branch=master
    :target: https://travis-ci.org/switchboardpy/switchboard

Switchboard is a port of Gargoyle, a feature flipper for Django apps, to
the Pyramid or Pylons stack (including TurboGears). Originally used to
selectively roll out changes to the SourceForge site, the library lets
you easily control whether a particular change (a switch) is active.

You can make switches active for a certain percentage of visitors, all
visitors to a particular host in a cluster, or if a particular string is
present in the query string. Furthermore you can easily create your own
conditions to do fancier things like geo-targeting, specific users, etc.
In short, Switchboard turns you into a continuous deployment ninja.

* `Switchboard on GitHub (repository and issue tracker)
  <https://github.com/switchboardpy/switchboard/>`_
* `Switchboard on PyPI <http://pypi.python.org/pypi/switchboard/>`_

Switchboard's basic unit is a switch. Every switch has a unique key
associated with it and is either active (on) or inactive (off), so using
it in code is simple::

    >>> from switchboard import operator
    >>> operator.is_active('foo')
    False

In this case we checked to see if the "foo" switch was active. By
default, Switchboard will auto-create any switches that don't already
exist, such as "foo". Auto-created switches default to an inactive
state.

Whether a switch is active or not is controlled by two attributes:
status and condition sets. There are four different statuses:

* Inactive - disabled for everyone
* Selective - active only for matched conditions
* Inherit - inherit from the parent switch
* Global - active for everyone

Inactive and global are opposite extremes: the switch is turned on or
off for everyone. The full docs cover parent-child switches, which
involves the inherit status. The selective status involves the second
attribute, condition sets. When a switch is in seletive status,
Switchboard checks the condition sets on the switch to see if it should
be active. Conditions are criteria such as "10% of all visitors" or
"only logged in users" that can be applied to the request to see if the
switch should be active. When a switch is in selective status, it will
only be active if it meets the conditions in place.

Switchboard's switches and their condition sets are controlled via the
admin UI. Adding switches to your code is as easy as importing the
global operator object, as demonstrated above. While there is much more
to Switchboard, such as parent-child switches, creating your own
conditoion sets, and setting up default settings for certain types of
switches, the quick intro above should give you a taste of what it's
capable of doing.
