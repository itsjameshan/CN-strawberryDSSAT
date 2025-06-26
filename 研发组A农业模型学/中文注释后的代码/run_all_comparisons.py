#!/usr/bin/env python3
"""Run validation for all strawberry experiments automatically."""
# 指定脚本运行时使用的 Python 解释器路径，并添加脚本的描述性注释

import os
import subprocess
import sys
from pathlib import Path
# 导入所需的 Python 模块，用于操作系统交互、子进程调用、获取系统信息以及处理路径

def run_validation(srx_file, output_dir="validation_results"):
    """Run validation for a single experiment file."""
    # 定义一个函数，用于对单个实验文件进行验证，接收实验文件路径和输出目录作为参数，默认输出目录为 validation_results

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    # 确保输出目录存在，如果不存在则创建，exist_ok=True 表示如果目录已存在，不会报错

    # Generate report filename
    experiment_name = Path(srx_file).stem
    report_file = f"{output_dir}/{experiment_name}_validation.txt"
    # 从实验文件路径中提取实验名称（去掉扩展名），并生成验证报告文件的完整路径

    try:
        print(f"\n{'='*60}")
        print(f"Running validation for: {experiment_name}")
        print(f"{'='*60}")
        # 打印分隔线和当前验证的实验名称，用于区分不同实验的验证过程

        # Run the validation
        result = subprocess.run([
            sys.executable, "validate_models.py", 
            srx_file,
            "--dssat-dir", "dssat-csm-os-develop",
            "--tolerance", "1.0",
            "--report", report_file
        ], capture_output=True, text=True, check=True)
        # 调用 subprocess.run 启动一个子进程来运行验证脚本 validate_models.py
        # sys.executable 获取当前 Python 解释器路径，确保使用相同的 Python 环境运行验证脚本
        # 传递实验文件路径、DSSAT 目录、容差值和报告文件路径作为参数
        # capture_output=True 捕获子进程的标准输出和标准错误输出
        # text=True 将输出以文本形式返回
        # check=True 如果子进程返回非零退出码，会抛出 CalledProcessError 异常

        print(result.stdout)
        print(f"✅ PASSED: {experiment_name}")
        print(f"   Report saved to: {report_file}")
        return True
        # 如果验证成功，打印子进程的标准输出、验证通过信息和报告文件保存位置，返回 True 表示验证成功

    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {experiment_name}")
        print(f"   Error: {e}")
        if e.stdout:
            print(f"   Output: {e.stdout}")
        if e.stderr:
            print(f"   Error details: {e.stderr}")
        return False
        # 如果验证失败，捕获 CalledProcessError 异常，打印验证失败信息、错误信息、子进程的标准输出和标准错误输出（如果存在），返回 False 表示验证失败

def main():
    """Run validation for all strawberry experiments."""
    # 定义主函数，用于运行所有草莓实验的验证

    # Find all strawberry experiment files
    strawberry_dir = "dssat-csm-data-develop/Strawberry"
    srx_files = list(Path(strawberry_dir).glob("*.SRX"))
    # 指定草莓实验文件所在的目录，并使用 glob 方法查找该目录下所有扩展名为 .SRX 的实验文件

    if not srx_files:
        print(f"No .SRX files found in {strawberry_dir}")
        return
    # 如果没有找到任何实验文件，打印提示信息并退出函数

    print(f"Found {len(srx_files)} strawberry experiments to validate:")
    for f in srx_files:
        print(f"  - {f.name}")
    # 打印找到的实验文件数量，并列出每个实验文件的名称

    # Run validation for each experiment
    results = {}
    for srx_file in srx_files:
        success = run_validation(str(srx_file))
        results[srx_file.stem] = success
    # 遍历每个实验文件，调用 run_validation 函数进行验证，并将验证结果存储到 results 字典中，键为实验名称，值为验证是否成功

    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    # 打印验证总结的分隔线和标题

    passed = sum(results.values())
    total = len(results)
    # 计算通过验证的实验数量和总实验数量

    for experiment, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{experiment:15} : {status}")
    # 遍历 results 字典，打印每个实验的名称和验证状态

    print(f"\nOverall: {passed}/{total} experiments passed validation")
    # 打印总体验证结果

    if passed == total:
        print("🎉 All validations PASSED! Your Python model is fully validated!")
    else:
        print(f"⚠️  {total - passed} validation(s) failed. Check individual reports.")
    # 根据验证结果，打印相应的提示信息

if __name__ == "__main__":
    main()
# 判断当前脚本是否作为主程序运行，如果是，则调用 main 函数