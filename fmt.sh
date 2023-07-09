#!/bin/bash

if [[ -z $VIRTUAL_ENV ]]; then
  echo "Virtual Environment not activated!"
  exit 1
fi

BLACK="$VIRTUAL_ENV/bin/black"
FILES=$(git status | grep -E '\.py[ocd]?$' | awk '{if (system("[ -f " $2 " ]") == 0) print $2}')

if [[ -n $FILES ]]; then
  echo $FILES | xargs $BLACK
else
  echo "No Python files to format."
fi

