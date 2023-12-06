import io
import re
from setuptools import setup


def get_version_from_debian_changelog():
    try:
        with io.open('debian/changelog', encoding='utf8') as stream:
            return re.search(r'\((.+)\)', next(stream)).group(1)
    except Exception:
        return '0.0.1'


setup(
    name='confight',
    version=get_version_from_debian_changelog(),
    description='Common config loading for Python and the command line',
    license='MIT',
    author='Avature',
    author_email='platform@avature.net',
    url='https://github.com/avature/confight',
    keywords='config configuration droplets toml json ini yaml',
    long_description=io.open('README.md', encoding='utf8').read(),
    long_description_content_type='text/markdown',
    py_modules=['confight'],
    install_requires=io.open('requirements.txt').read().splitlines(),
    extras_require={
        'yaml': ["ruamel.yaml"],
    },
    entry_points={
        'console_scripts': [
            'confight = confight:cli',
        ]
    },
    classifiers=(
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
