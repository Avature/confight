#!/bin/bash -eu
echo "Cleaning dist directory"
rm -f dist/*

echo "Building python packages"
python setup.py sdist
python setup.py bdist_wheel
python3 setup.py bdist_wheel
echo "Generated python packages"

echo "Uploading to test repository"
twine upload --repository pypitest dist/*
#twine upload --repository pypi dist/*
