@echo off
rem Build and install DSSAT-CSM using MinGW on Windows
mkdir build 2>NUL
cd build
cmake .. -G "MinGW Makefiles"
mingw32-make
mingw32-make install
