import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

setup(
    name='moonsheep',
    version='0.1.0',
    packages=['moonsheep'],
    description='digitization of public documents',
    long_description=README,
    author='TransparenCEE',
    author_email='ppeczek@epf.org.pl',
    url='https://github.com/TransparenCEE/moonsheep/',
    license='AGPL-3.0',
    include_package_data=True,
    install_requires=[
        'Django>=1.11',
    ]
)