from __future__ import unicode_literals
from __future__ import absolute_import
import setuptools

VERSION = '1.5.3'
INSTALL_REQUIRES = [
    'pymongo >= 3',
    'blinker >= 1.2',
    'WebOb >= 0.9',
    'Mako >= 0.9',
    'bottle >= 0.12.8',
    'six',
]

setuptools.setup(
    name='switchboard',
    version=VERSION,
    description="Feature flipper for Pyramid, Pylons, or TurboGears apps.",
    # http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.7',
    keywords='switches feature flipper pyramid pylons turbogears',
    author='Kyle Adams',
    author_email='kadams54@users.noreply.github.com',
    url='https://github.com/switchboardpy/switchboard/',
    download_url='https://github.com/switchboardpy/switchboard/releases',
    license='Apache License',
    packages=setuptools.find_packages(exclude=['ez_setup']),
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    zip_safe=False,
    tests_require=[
        'nose',
        'mock',
        'paste',
        'selenium >= 3.0',
        'splinter',
    ],
    test_suite='nose.collector',
)
