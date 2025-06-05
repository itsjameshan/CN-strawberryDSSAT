@echo off
rem Build, install, and run DSSAT-CSM with sample strawberry data using MinGW

if not exist build mkdir build
cd build
cmake .. -G "MinGW Makefiles"
mingw32-make
mingw32-make install

set DSSATDIR=C:\DSSAT48

rem Copy sample experiments and weather files
xcopy "..\..\dssat-csm-data-develop\Strawberry\*" "%DSSATDIR%\Strawberry" /Y /I
xcopy "..\..\dssat-csm-data-develop\Weather\*.WTH" "%DSSATDIR%\Strawberry" /Y /I

rem Use the provided batch file for strawberry simulations
copy "..\..\dssat-csm-os-develop\Data\BatchFiles\Strawberry.v48" "%DSSATDIR%\BatchFiles\STRB.V48" >nul

cd "%DSSATDIR%\BatchFiles"
..\dscsm048.exe CRGRO048 B STRB.V48

