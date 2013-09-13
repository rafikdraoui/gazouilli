import io
from setuptools import setup, find_packages

import gazouilli


with io.open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='gazouilli',
    version=gazouilli.__version__,
    url='https://github.com/rafikdraoui/gazouilli/',
    author='Rafik Draoui',
    author_email='rafik@rafik.ca',
    license='MIT',
    description=gazouilli.__doc__,
    long_description=long_description,

    packages=find_packages(),
    install_requires=['numpy'],
    entry_points={
        'console_scripts': ['gazouilli = gazouilli.cli:run'],
    },
)
