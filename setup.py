import io
import re

from setuptools import setup


def get_version_from_debian_changelog():
    try:
        with io.open("debian/changelog", encoding="utf8") as stream:
            return re.search(r"\((.+)\)", next(stream)).group(1)
    except Exception:
        return "0.0.1"


setup(
    name="confight",
    version=get_version_from_debian_changelog(),
    description="Common config loading for Python and the command line",
    license="MIT",
    author="Avature",
    author_email="platform@avature.net",
    url="https://github.com/avature/confight",
    keywords="config configuration droplets toml json ini yaml",
    long_description=io.open("README.md", encoding="utf8").read(),
    long_description_content_type="text/markdown",
    py_modules=["confight"],
    install_requires=io.open("requirements.txt").read().splitlines(),
    extras_require={
        "yaml": ["ruamel.yaml>=0.18.0"],
        "hcl": ["pyhcl"],
    },
    entry_points={
        "console_scripts": [
            "confight = confight:cli",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
