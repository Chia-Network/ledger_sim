"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.org'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='ledger_sim',
    version='0.20190701',
    description='Chia network ledger sim',
    long_description=long_description,
    long_description_content_type='text/plain',
    url='https://github.com/Chia-Network',
    author='Chia Network',
    author_email='hello@chia.net',
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Apache License',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='chia cryptocurrency',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    python_requires='>=3.6, <4',
    install_requires=[],

    extras_require={
        'dev': [],
        'test': ['coverage'],
    },
    entry_points={
        'console_scripts': [
            'ledger-sim=chiasim.cmds.ledger_sim:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/Chia-Network',
        'Source': 'https://github.com/Chia-Network',
    },
    package_data={
        '': ['*.clvm'],
    },
)
