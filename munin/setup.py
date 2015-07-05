import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "Munin plugins",
    version = "0.1",
    author = "Stefan Midjich",
    author_email = "swehack@gmail.com",
    description = "These are custom munin plugins.",
    license = "BSD",
    keywords = "munin spamassassin",
    url = "https://github.com/stemid/devops",
    packages = find_packages(),
    scripts = ['spamassassin_timing.py'],
    long_description = read('README.md'),
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: BSD License",
    ],
)
