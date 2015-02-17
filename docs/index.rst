.. Switchboard documentation master file, created by
   sphinx-quickstart on Thu Mar 13 12:31:24 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Switchboard
======================

Switchboard is a feature flipper library for the Pyramid or Pylons stacks
(including TurboGears). Originally used to selectively roll out changes to the
SourceForge site, the library lets you easily control whether a particular
change (a switch) is active.

You can make switches active for a certain percentage of visitors, all
visitors to a particular host in a cluster, or if a particular string is
present in the query string. Furthermore you can easily create your own
conditions to do fancier things like geo-targeting, specific users, etc.

Having a `feature flipper`_ allows features to be inserted without creating
long-running feature branches. Not having to deal with merge headaches
and messy conflicts means your continuous integration builds run smoother.
`Continous deployment`_ is now an option because dangerous code can be hidden
behind a switch. In short, Switchboard turns you into a `continuous delivery
ninja`_.

.. _`feature flipper`: https://en.wikipedia.org/wiki/Feature_toggle
.. _`Continuous deployment`: https://en.wikipedia.org/wiki/Continuous_delivery
.. _`continuous delivery ninja`: http://code.flickr.net/2009/12/02/flipping-out/

Documentation
-------------

.. toctree::
   :maxdepth: 2

   user-documentation


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

