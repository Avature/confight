#!/bin/bash -eu
echo "Cleaning dist directory"
rm -f dist/*

echo "Building python packages"
python3 setup.py bdist_wheel
echo "Generated python packages"

echo "Uploading to test repository"
#twine upload --repository testpypi dist/*
twine upload --repository pypi-confight dist/*
