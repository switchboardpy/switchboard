from setuptools import setup, find_packages

version = '1.0.6'

setup(name='switchboard',
      version=version,
      description="Feature flipper for Pyramid, Pylons, or TurboGears apps.",
      # http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='switches feature flipper pyramid pylons turbogears',
      author='Kyle Adams',
      author_email='kadams54@users.sourceforge.net',
      url='http://sf.net/projects/switchboardpy',
      download_url='https://sf.net/projects/switchboardpy/files/latest',
      license='Apache License',
      packages=find_packages(exclude=['ez_setup']),
      include_package_data=True,
      install_requires=[
          'FormEncode >= 1.2',
          'pymongo >= 2.3',
          'blinker >= 1.2',
          'WebOb >= 0.9',
          'Jinja2 >= 2.6',
          'pylibmc >= 1.2',
          'decorator',
      ],
      zip_safe=False,
      tests_require=[
        'nose >= 0.11',
        'mock >= 1.0',
      ],
      test_suite='nose.collector',
      )
