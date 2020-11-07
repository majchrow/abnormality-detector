from setuptools import setup

setup(
    name='bridge-connector',
    packages=['connector'],
    entry_points={
        'console_scripts': ['bridge-connector=connector.main:main'],
    }
)
