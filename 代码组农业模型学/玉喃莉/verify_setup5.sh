#!/usr/bin/env bash

# 验证脚本 - 检查setup_windows5.sh是否包含所有修复
# Verification script - Check if setup_windows5.sh contains all fixes

echo "=== 验证 setup_windows5.sh 文件 ==="
echo "=== Verifying setup_windows5.sh file ==="
echo ""

# 检查文件是否存在
if [ ! -f "setup_windows5.sh" ]; then
    echo "❌ 错误: setup_windows5.sh 文件不存在"
    echo "❌ Error: setup_windows5.sh file does not exist"
    exit 1
fi

echo "✅ setup_windows5.sh 文件存在"
echo "✅ setup_windows5.sh file exists"
echo ""

# 检查关键函数是否存在
echo "检查关键函数 / Checking key functions:"
echo ""

# 1. 网络连接测试函数
if grep -q "test_network_connectivity()" setup_windows5.sh; then
    echo "✅ test_network_connectivity() 函数存在"
else
    echo "❌ test_network_connectivity() 函数缺失"
fi

# 2. 网络问题修复函数
if grep -q "fix_network_issues()" setup_windows5.sh; then
    echo "✅ fix_network_issues() 函数存在"
else
    echo "❌ fix_network_issues() 函数缺失"
fi

# 3. pip替代安装函数
if grep -q "install_pip_alternative()" setup_windows5.sh; then
    echo "✅ install_pip_alternative() 函数存在"
else
    echo "❌ install_pip_alternative() 函数缺失"
fi

# 4. CMake替代安装函数
if grep -q "install_cmake_alternative()" setup_windows5.sh; then
    echo "✅ install_cmake_alternative() 函数存在"
else
    echo "❌ install_cmake_alternative() 函数缺失"
fi

# 5. Fortran编译器替代安装函数
if grep -q "install_fortran_alternative()" setup_windows5.sh; then
    echo "✅ install_fortran_alternative() 函数存在"
else
    echo "❌ install_fortran_alternative() 函数缺失"
fi

# 6. 构建工具替代安装函数
if grep -q "install_build_tools_alternative()" setup_windows5.sh; then
    echo "✅ install_build_tools_alternative() 函数存在"
else
    echo "❌ install_build_tools_alternative() 函数缺失"
fi

echo ""

# 检查重试机制
echo "检查重试机制 / Checking retry mechanisms:"
if grep -q "for attempt in 1 2 3" setup_windows5.sh; then
    echo "✅ 重试机制存在 (3次重试)"
else
    echo "❌ 重试机制缺失"
fi

# 检查网络连接测试调用
if grep -q "test_network_connectivity" setup_windows5.sh; then
    echo "✅ 网络连接测试调用存在"
else
    echo "❌ 网络连接测试调用缺失"
fi

echo ""

# 检查文件大小
FILE_SIZE=$(wc -c < setup_windows5.sh)
echo "文件大小 / File size: $FILE_SIZE bytes"

# 检查行数
LINE_COUNT=$(wc -l < setup_windows5.sh)
echo "行数 / Line count: $LINE_COUNT lines"

echo ""

# 检查是否包含中文错误信息
if grep -q "网络连接问题" setup_windows5.sh; then
    echo "✅ 包含中文错误信息"
else
    echo "❌ 缺少中文错误信息"
fi

# 检查是否包含英文错误信息
if grep -q "Network connectivity issues" setup_windows5.sh; then
    echo "✅ 包含英文错误信息"
else
    echo "❌ 缺少英文错误信息"
fi

echo ""
echo "=== 验证完成 ==="
echo "=== Verification completed ==="

# 总结
echo ""
echo "总结 / Summary:"
echo "- 如果所有项目都显示 ✅，说明修复已正确复制"
echo "- If all items show ✅, the fixes have been correctly copied"
echo "- 如果任何项目显示 ❌，说明需要重新检查"
echo "- If any item shows ❌, re-checking is needed" 