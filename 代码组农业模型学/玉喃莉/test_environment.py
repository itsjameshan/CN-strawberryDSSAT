#!/usr/bin/env python3
"""测试Python环境和依赖是否正确安装"""

import sys
import importlib

def test_imports():
    """测试必要的库是否可以导入"""
    required_packages = [
        'numpy',
        'pandas', 
        'matplotlib',
        'scipy',
        'numba'
    ]
    
    print("测试Python环境...")
    print(f"Python版本: {sys.version}")
    print()
    
    failed_imports = []
    
    for package in required_packages:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', '未知版本')
            print(f"✓ {package}: {version}")
        except ImportError as e:
            print(f"✗ {package}: 导入失败 - {e}")
            failed_imports.append(package)
    
    print()
    
    if failed_imports:
        print("以下包需要安装:")
        for package in failed_imports:
            print(f"  pip install {package}")
        return False
    else:
        print("所有依赖包都已正确安装!")
        return True

def test_strawberry_implementation():
    """测试草莓模型实现是否可以导入"""
    try:
        import importlib.util
        import pathlib
        
        impl_path = pathlib.Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"
        
        if not impl_path.exists():
            print(f"✗ 草莓模型实现文件不存在: {impl_path}")
            return False
            
        spec = importlib.util.spec_from_file_location("cropgro_strawberry_implementation", impl_path)
        if spec is None:
            print("✗ 无法创建模块规范")
            return False
            
        impl_module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            print("✗ 无法获取模块加载器")
            return False
            
        spec.loader.exec_module(impl_module)
        CropgroStrawberry = impl_module.CropgroStrawberry
        
        print("✓ 草莓模型实现可以正确导入")
        return True
        
    except Exception as e:
        print(f"✗ 草莓模型实现导入失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("DSSAT草莓模型环境测试")
    print("=" * 50)
    print()
    
    imports_ok = test_imports()
    print()
    
    if imports_ok:
        strawberry_ok = test_strawberry_implementation()
        print()
        
        if strawberry_ok:
            print("✓ 环境测试通过! 可以运行草莓模型了。")
        else:
            print("✗ 草莓模型实现有问题，请检查文件。")
    else:
        print("✗ 请先安装缺失的依赖包。")
        print()
        print("运行以下命令安装依赖:")
        print("pip install -r requirements.txt") 