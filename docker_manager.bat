@echo off
REM DSSAT-CROPGRO Strawberry Docker管理器 - Windows版本
REM 使用方法: docker_manager.bat <命令> [参数]

setlocal enabledelayedexpansion

REM 配置变量 - 请根据您的实际路径修改
set PROJECT_DIR=C:\Users\cheng\Downloads\CN-strawberryDSSAT-main
set DOCKER_IMAGE_NAME=dssat-cropgro-strawberry
set CONTAINER_NAME=strawberry-model