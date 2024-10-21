from setuptools import find_packages, setup
import os

# Get more https://pypi.org/pypi?%3Aaction=list_classifiers
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    # Indicate to who your project is directed
    "Environment :: Web Environment",
    "Framework :: Django",
    "Intended Audience :: Developers",
    # Indicate the used license (must match the "license")
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Operating System :: OS Independent",
    # Indicate supported versions, Python 2, Python 3 or both.
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.5",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    "Topic :: Internet :: WWW/HTTP :: WSGI",
    "Topic :: Software Development",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

EXCLUDE_FROM_PACKAGES = ["project","project.*"]

def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()

setup(
    name="django-helloworld",
    version="0.1",
    description="A Django 'Hello World' program example",
    long_description=read('README.rst'),
    classifiers=CLASSIFIERS,
    keywords="example helloworld django program",
    author="Alex Clark",
    author_email="aclark@aclark.net",
    maintainer="Leonardo J. Caballero G.",
    maintainer_email="leonardocaballero@gmail.com",
    url="https://github.com/django-ve/django-helloworld",
    license="GPL",
    platforms="OS Independent",
    install_requires=["Django==2.2.3"],
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    zip_safe=False,
    project_urls={
        'Documentation': 'https://docs.djangoproject.com/',
        'Funding': 'https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=KX6MCYREN2BR2&lc=VE&item_name=lcaballero%2ewordpress%2ecom&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted',
        'Source': 'https://github.com/django-ve/django-helloworld',
        'Tracker': 'https://github.com/django-ve/buildout.django/issues',
    },
)
