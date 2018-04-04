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
    author='Platform',
    author_email='platform@avature.net',
    py_modules=['confight'],
    install_requires=open('requirements.txt').read().splitlines(),
    extras_require={
        'yaml': ["ruamel.yaml"],
    }
)
