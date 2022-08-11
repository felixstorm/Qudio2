#!/bin/bash
set -euo pipefail


echo "*** $(realpath $BASH_SOURCE) Starting on $(hostname -A) ($(hostname -I))"


PYC_PATHS=($(python3 -c "import sys; print(next(x for x in sys.path if x.startswith('/usr/local/')))") $(realpath $(dirname $BASH_SOURCE)))
echo "Using PYC_PATHS: ${PYC_PATHS[@]}"


if echo $* | grep -E "(^|\s)(-f|--force)($|\s)" -q; then
    echo 'Deleting all existing *.pyc files...'
    find "${PYC_PATHS[@]}" -name '*.pyc' -delete
    echo '  Done.'
fi


echo 'Running python3 compileall...'
python3 -m compileall "${PYC_PATHS[@]}" | { grep -E --invert-match '^Listing ' || true; }
echo '  Done.'


echo "*** $(realpath $BASH_SOURCE) Completed"
