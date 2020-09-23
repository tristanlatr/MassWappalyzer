
#! /usr/bin/env python3
from setuptools import setup
import sys
if sys.version_info[0] < 3: raise RuntimeError("Sorry, you must use Python 3")
# The directory containing this file
import pathlib
import os
HERE = pathlib.Path(__file__).parent
# The text of the README file
README = (HERE / "README.md").read_text()
setup(
    name                =   'masswappalyzer',
    description         =   "Run Wappalyzer asynchronously on a list of URLs and generate a Excel file containing all results.",
    url                 =   "https://github.com/tristanlatr/MassWappalyzer",
    maintainer          =   "tristanlatr",
    version             =   '1.4',
    entry_points        =   {'console_scripts': ['masswappalyzer = masswappalyzer:main'],},
    py_modules          =   ['masswappalyzer'], 
    classifiers         =   ["Programming Language :: Python :: 3"],
    license             =   'Apache License 2.0',
    long_description    =   README,
    long_description_content_type   =   "text/markdown",
    install_requires    =   ['XlsxWriter', 'tqdm', 'pandas', 'requests', 'lxml', 'aiohttp', 'python-Wappalyzer>=0.3.0']  
)
