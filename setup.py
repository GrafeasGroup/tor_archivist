import codecs
import os
import sys

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

from tor_archivist import __version__


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


def long_description():
    if not (os.path.isfile('README.rst') and os.access('README.rst', os.R_OK)):
        return ''

    with codecs.open('README.rst', encoding='utf8') as f:
        return f.read()


test_deps = [
    'pytest',
    'pytest-cov',
    'sh',
]
dev_helper_deps = [
    'better-exceptions',
]


setup(
    name='tor_archivist',
    version=__version__,
    description='The officially licensed archivist for /r/TranscribersOfReddit!',
    long_description=long_description(),
    url='https://github.com/GrafeasGroup/tor_archivist',
    author='Joe Kaufeld',
    author_email='joe.kaufeld@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',

        'Intended Audience :: End Users/Desktop',
        'Topic :: Communications :: BBS',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='',
    packages=find_packages(exclude=['test', 'test.*', '*.test.*', '*.test']),
    zip_safe=True,
    cmdclass={'test': PyTest},
    test_suite='test',
    entry_points={
        'console_scripts': [
            'tor-archivist = tor_archivist.main:main',
        ],
    },
    extras_require={
        'dev': test_deps + dev_helper_deps,
    },
    tests_require=test_deps,
    install_requires=[
        'praw==5.0.1',
        'redis<3.0.0',
        'sh',
        'cherrypy',
        'bugsnag',
        'raven',  # Sentry client
        'requests',
        'slackclient<2.0.0',
    ],
)
