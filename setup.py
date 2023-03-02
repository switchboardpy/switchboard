import setuptools
from pathlib import Path

VERSION = '1.6.3'
INSTALL_REQUIRES = [
    'pymongo >= 3, < 4',
    'blinker >= 1.2',
    'WebOb >= 0.9',
    'Mako >= 0.9',
    'bottle >= 0.12.8',
]

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setuptools.setup(
    name='switchboard',
    version=VERSION,
    description="Feature flipper for Pyramid, Pylons, or TurboGears apps.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    # http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
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
        'pytest',
        'selenium >= 3.0',
        'splinter',
    ],
)
