#!/bin/bash -eu

if test $# -ne 1; then
    echo "Missing version number"
    exit 1
fi

if ! command -v gbp &> /dev/null; then
    echo "Missing gbp command"
    echo "Install git-buildpackage"
    echo "  sudo apt-get install -yq git-buildpackage"
    exit 1
fi

declare -r VERSION=$1
declare -rx DEBFULLNAME=Platform
declare -rx DEBEMAIL=platform@avature.net

echo "Running tests"
tox --recreate > /dev/null
gbp dch \
    --new-version $VERSION \
    --distribution unstable \
    --debian-tag="%(version)s"\
    --no-git-author\
    --id-length=8\
    --spawn-editor=always
python write_changelog.py
git commit -am "Bumps version $VERSION"
git tag $VERSION -am "Version $VERSION"
echo "Created tag $VERSION"
echo "Don't forget to: "
echo " git push origin master"
echo " git push origin $VERSION"
