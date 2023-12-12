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
declare -rx DEBFULLNAME="Platform Operability"
declare -rx DEBEMAIL=platformoperability@avature.net

echo "Running tests"
#tox --recreate > /dev/null
gbp dch \
    --new-version $VERSION \
    --distribution $(lsb_release -sc) \
    --debian-tag="%(version)s"\
    --no-git-author\
    --id-length=8\
    --spawn-editor=always
python write_changelog.py
sed -i "s/#VERSION#/$VERSION/g" README.md
sed -i "s/^__version__ = .*$/__version__ = '$VERSION'/g" confight.py
git commit -am "Bumps version $VERSION"
git tag -s $VERSION -am "Version $VERSION"
echo "Created tag $VERSION"
echo "Don't forget to: "
echo " git push origin master $VERSION"
