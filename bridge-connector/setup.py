from setuptools import setup

setup(
    name='bridge-connector',
    packages=['connector', 'connector.client'],
    python_requires='>=3.8',
    package_dir = {'': 'src'},
    entry_points={
        'console_scripts': ['bridge-connector=connector.main:main'],
    }
)
