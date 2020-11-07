from setuptools import setup

setup(
    name='bridge-connector',
    packages=['connector', 'connector.client'],
    entry_points={
        'console_scripts': ['bridge-connector=connector.main:main'],
    }
)
