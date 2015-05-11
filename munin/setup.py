import os
from setuptools import setup
from distutils.command.install_scripts import install_scripts

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

class my_install_scripts(install_scripts):
    def run(self):
        self.install_dir = '/usr/share/munin/plugins'
        install_scripts.run(self)

    def write_script(self, script_name, contents, mode="t", *ignored):
        script_name = script_name.split('.py')[0]
        install_scripts.write_script(self, script_name, contents, mode, ignored)

setup(
    name = "Munin plugins",
    version = "0.1",
    author = "Stefan Midjich",
    author_email = "swehack@gmail.com",
    description = ("These are custom munin plugins."),
    license = "BSD",
    keywords = "munin spamassassin",
    url = "https://github.com/stemid/devops",
    packages = None,
    scripts = ['spamassassin_timing.py'],
    long_description = read('README.md'),
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: BSD License",
    ],
    cmdclass = {'install_scripts': my_install_scripts},
)
