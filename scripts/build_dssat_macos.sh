#!/usr/bin/env bash

# Build, install, and run DSSAT-CSM with sample strawberry data on macOS
set -euo pipefail

# Compile the Fortran sources
cd "$(dirname "$0")/../dssat-csm-os-develop"
mkdir -p build
cd build
cmake -DCMAKE_INSTALL_PREFIX=$HOME/dssat ..
make
make install

# Install sample strawberry experiments and weather files
mkdir -p $HOME/dssat/Strawberry
cp ../../dssat-csm-data-develop/Strawberry/* $HOME/dssat/Strawberry/
cp ../../dssat-csm-data-develop/Weather/*.WTH $HOME/dssat/Strawberry/

# Create BatchFiles directory and batch file
mkdir -p $HOME/dssat/BatchFiles

# Create symbolic link to expected DSSAT path (requires sudo)
sudo mkdir -p /DSSAT48
sudo ln -sf $HOME/dssat/* /DSSAT48/

# Create DSSAT configuration file
tee $HOME/dssat/DSSATPRO.L48 > /dev/null <<'CONFIG'
*DSSAT 4.8 CONFIGURATION FILE
! Default settings for DSSAT

$BATCH(STRAWBERRY)
CONFIG

tee $HOME/dssat/BatchFiles/STRB.V48 > /dev/null <<'BATCH'
$BATCH(STRAWBERRY)
@FILEX
              TRTNO     RP     SQ     OP     CO
../Strawberry/UFBA1401.SRX           1      1      0      1      0
../Strawberry/UFBA1601.SRX           1      1      0      1      0
../Strawberry/UFBA1601.SRX           2      1      0      1      0
../Strawberry/UFBA1701.SRX           1      1      0      1      0
../Strawberry/UFBA1701.SRX           2      1      0      1      0
../Strawberry/UFWM1401.SRX           1      1      0      1      0
../Strawberry/UFWM1401.SRX           2      1      0      1      0
BATCH

# Run the strawberry model
cd $HOME/dssat/BatchFiles
../dscsm048 CRGRO048 B STRB.V48

