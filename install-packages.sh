#!/bin/bash

set -e
PYTHON="python3.8"

# ___________________________________________________________________________
# Create virtural environment
if [ ! -d "venv" ]; then
    echo -e "\nCreating virtual environment ..."
    $PYTHON -m venv "venv"
fi
echo -e "\nActivating virtual environment"
source venv/bin/activate

# ___________________________________________________________________________
# List Python packages
echo -e "\nPackages installed"
$PYTHON -m pip list --no-color
echo -e "\nPackages outdated"
$PYTHON -m pip list --no-color --outdated

# ___________________________________________________________________________
# Setup base enviorment
echo -e "\nUpdate baseline packages"
$PYTHON -m pip install --no-color --compile --upgrade pip
$PYTHON -m pip install --no-color --compile --upgrade setuptools wheel

# ___________________________________________________________________________
# Install/Update packeages from requirements
if [ -f "requirements.txt" ]; then
    echo -e "\nInstall from requirements.txt"
    $PYTHON -m pip install --no-color --compile --upgrade-strategy eager --upgrade --requirement requirements.txt
    $PYTHON -m pip list --no-color
else
    echo -e "\nNo requirements.txt found"
fi

