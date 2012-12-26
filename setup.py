from setuptools import setup, find_packages

version = '1.0'

setup(name='switchboard',
      version=version,
      description="Feature flipper for pyramid and pylons apps.",
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Kyle Adams',
      author_email='kadams54@users.sourceforge.net',
      url='',
      license='Apache License',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['switchboard'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'pymongo >= 1.9',
      ],
      tests_require=[
        'nose >= 0.11.1',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      test_suite='nose.collector',
      )
