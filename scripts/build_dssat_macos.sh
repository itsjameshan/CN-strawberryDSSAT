#!/usr/bin/env bash

# Build, install, and run DSSAT-CSM with sample strawberry data on macOS
set -euo pipefail

# Compile the Fortran sources
=======
# Build and install DSSAT-CSM on macOS
set -euo pipefail

cd "$(dirname "$0")/../dssat-csm-os-develop"
mkdir -p build
cd build
cmake ..
make
sudo make install


# Install sample strawberry experiments and weather files
sudo mkdir -p /usr/local/Strawberry
sudo cp ../../dssat-csm-data-develop/Strawberry/* /usr/local/Strawberry/
sudo cp ../../dssat-csm-data-develop/Weather/*.WTH /usr/local/Strawberry/

# Create a batch file referencing the local installation
sudo tee /usr/local/BatchFiles/STRB.V48 > /dev/null <<'BATCH'
$BATCH(STRAWBERRY)
! Directory    : /usr/local/Strawberry
! Command Line : /usr/local/dscsm048 CRGRO048 B STRB.V48
@FILEX
              TRTNO     RP     SQ     OP     CO
/usr/local/Strawberry/UFBA1401.SRX           1      1      0      1      0
/usr/local/Strawberry/UFBA1601.SRX           1      1      0      1      0
/usr/local/Strawberry/UFBA1601.SRX           2      1      0      1      0
/usr/local/Strawberry/UFBA1701.SRX           1      1      0      1      0
/usr/local/Strawberry/UFBA1701.SRX           2      1      0      1      0
/usr/local/Strawberry/UFWM1401.SRX           1      1      0      1      0
/usr/local/Strawberry/UFWM1401.SRX           2      1      0      1      0
BATCH

# Run the strawberry model
cd /usr/local/BatchFiles
../dscsm048 CRGRO048 B STRB.V48

=======

