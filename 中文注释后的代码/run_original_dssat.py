"""Helper script to execute the original DSSAT strawberry model."""

#导入模块
import argparse  # 用于解析命令行参数，方便用户通过命令行指定输入文件、目录等。
import os  # 提供操作系统相关的功能，如文件路径操作等。
import shutil  # 提供高级的文件操作功能，如文件复制等
import subprocess  # 用于运行外部程序，这里用于调用DSSAT模型。
from pathlib import Path  #来自pathlib模块，用于操作文件系统路径，比传统的os.path更现代、更方便。


#定义主函数
def main():  #脚本的主入口函数，所有逻辑都在这个函数中实现 
    parser = argparse.ArgumentParser(
        description="Execute the original DSSAT strawberry model on macOS"  # 创建一个ArgumentParser对象，用于解析命令行参数。
    )
    parser.add_argument(
        "experiment",  # 添加一个位置参数experiment，这是必需的用户必须提供一个DSSAT实验文件的路径
        help="Path to a DSSAT .SRX experiment file",
    ) #help参数提供了该参数的说明信息
    parser.add_argument(
        "--dssat-dir",  # 添加一个可选参数--dssat-dir，用于指定DSSAT安装目录的路径
        default="dssat-csm-os-develop",#默认值为dssat-csm-os-develop，如果用户没有指定该参数，则使用这个默认值。
        help=(
            "Directory containing the DSSAT build or installation. "
            "Must include Utilities/run_dssat"  #help参数提供了该参数的说明信息，强调必须包含Utilities/run_dssat文件。
        ),
    )
       parser.add_argument(
        "--output-dir",  # 添加一个可选参数--output-dir，用于指定输出文件存放的目录。
        default="dssat_results",#默认值为dssat_results，如果用户没有指定该参数，则使用这个默认值
        help="Directory where output files will be copied",
    )
#解析命令参数
   args = parser.parse_args()  # 调用parse_args()方法解析命令行参数，将解析后的参数存储在args对象中。

    exp_path = Path(args.experiment).resolve()  
    dssat_dir = Path(args.dssat_dir).resolve()  
    out_dir = Path(args.output_dir).resolve()

 #构建DSSAT运行器 
    util = dssat_dir / "Utilities" / "run_dssat"  #构建run_dssat文件的路径，该文件是运行DSSAT模型的辅助工具。 
    if not util.exists():  #使用exists()方法检查该文件是否存在，如果不存在，则抛出FileNotFoundError异常。
        raise FileNotFoundError(f"run_dssat not found at {util}")

    # 执行DSSAT模型
    subprocess.run([str(util), exp_path.name], cwd=exp_path.parent, check=True)#使用subprocess.run()方法运行DSSAT模型，参数[str(util), exp_path.name]表示要运行的命令及其参数，str(util)将Path对象转换为字符串，
#创建输出目录
    out_dir.mkdir(parents=True, exist_ok=True)  #使用mkdir()方法创建输出目录，parents=True表示如果需要，会创建所有父目录，exist_ok=True表示如果目录已经存在，不会抛出异常。
#复制输出文件
    for name in ["summary.csv", "PlantGro.OUT"]:  # 遍历已知的输出文件名称列表["summary.csv", "PlantGro.OUT"]。
        src = exp_path.parent / name #对于每个文件，构建其源路径src
        if src.exists():#使用exists()方法检查文件是否存在，如果存在，则使用shutil.copy2()方法将其复制到输出目录。
）。
            shutil.copy2(src, out_dir / src.name)  # shutil.copy2()会保留文件的元数据（如修改时间等）

#确保脚本直接运行时才执行主函数
if __name__ == "__main__":  # 确保当脚本被直接运行时，才会调用main()函数。
    main()
