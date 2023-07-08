#!/bin/bash

if [[ -z $VIRTUAL_ENV ]]; then
  echo "Virtual Environment not activated!"
  exit 1
fi

BLACK="$VIRTUAL_ENV/bin/black"
git status | grep -E '\.py[ocd]?$' | awk '{print $2}' | xargs $BLACK
