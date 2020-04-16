#!/bin/bash

REPO_NAME="stock-prices"
CWD=${PWD##*/}

set -e

# Clone repository if not found
if [ $CWD == "$REPO_NAME" ] && [ ! -d ".git" ]; then
  echo Git repository not found
  echo Run script in parent directory but this directory $CWD must not exist or be empty
  exit 1
fi

if [ $CWD != "$REPO_NAME" ] && [ ! -d ".git" ]; then
  echo -e "\ngit cloning ..."
  git clone https://github.com/tycarac/$REPO_NAME.git
fi

if [ -d "$REPO_NAME" ] && [ -d "$REPO_NAME/.git" ]; then
  cd $REPO_NAME
fi

# Update
CWD=${PWD##*/}
if [ $CWD != "$REPO_NAME" ]; then
  echo -e "\nNot in directory $REPO_NAME"
  exit 2
fi

echo -e "\ngit fetching ..."
git fetch --all --prune

echo -e "\ngit merging ..."
git merge origin/master

echo -e "\n git status ..."
git status
