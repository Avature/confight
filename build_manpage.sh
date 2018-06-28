#!/bin/bash -eu
declare -r NAME=confight
declare -r AUTHOR=Avature
declare -r DATE=$(date +"%B %Y")

echo "Building man page"
mkdir -p docs
cat >> docs/README.md << EOF
% $NAME(1)
$AUTHOR
$DATE

EOF
cat README.md >> docs/README.md
pandoc docs/README.md --standalone -t man | \
    tee -a docs/${NAME}.1 docs/${NAME}3.1 &> /dev/null
