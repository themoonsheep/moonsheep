import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

setup(
    name='django-moonsheep',
    version='0.3.0',
    # packages=['moonsheep'],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'moonsheep': ['templates/*.html', 'templates/**/*.html']
    },
    description='digitization of public documents',
    long_description=README,
    author='TransparenCEE',
    author_email='ppeczek@epf.org.pl',
    url='https://github.com/TransparenCEE/moonsheep/',
    download_url='',
    test_suite='runtests.runtests',
    license='AGPL-3.0',
    install_requires=[
        'Django>=1.11',
        'pybossa-client~=2.0',
        'dpath~=1.4',
        'djangorestframework~=3.10',
        'djangorestframework-jsonapi~=2.8',
        'django-filter~=2.2',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11.7',  # replace "X.Y" as appropriate
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',  # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    zip_safe=False,
)
