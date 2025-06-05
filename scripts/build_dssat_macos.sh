#!/usr/bin/env bash
# Build and install DSSAT-CSM on macOS
set -euo pipefail
cd "$(dirname "$0")/../dssat-csm-os-develop"
mkdir -p build
cd build
cmake ..
make
sudo make install
