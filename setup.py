# -*- coding: utf-8 -*-

from setuptools import find_packages
from setuptools import setup

version = "1.0.0"

with open("README.rst", "r") as fh:
    long_description = fh.read()

with open("CHANGES.rst", "r") as fh:
    long_description += "\n\n"
    long_description += fh.read()

setup(
    name="bes.lims",
    version=version,
    description="SENAITE extension profile providing shared functionalities, "
                "customizations and configurations for laboratories "
                "implemented under the leadership of Beyond Essential Systems",
    long_description=long_description,
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Plone",
        "Framework :: Zope2",
    ],
    keywords="",
    author="NARALABS",
    author_email="info@naralabs.com",
    url="https://github.com/beyondessential/bes.lims",
    license="GPLv2",
    packages=find_packages(where="src", include=["bes*"]),
    package_dir={"": "src"},
    namespace_packages=["bes"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "senaite.lims>=2.5.0",
        "senaite.ast>=1.2.0",
        "senaite.patient>=1.5.0",
    ],
    extras_require={
        "test": [
            "plone.app.testing",
            "unittest2",
        ]
    },
    entry_points="""
        # -*- Entry points: -*-
        [z3c.autoinclude.plugin]
        target = plone
        """,
)
