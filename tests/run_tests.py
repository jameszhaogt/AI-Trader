#!/usr/bin/env python
"""
测试运行脚本
运行所有单元测试和集成测试
"""

import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def run_all_tests(verbosity=2):
    """运行所有测试
    
    Args:
        verbosity: 详细程度 (0=静默, 1=正常, 2=详细)
    
    Returns:
        bool: 所有测试是否通过
    """
    print("="*80)
    print(" "*25 + "AI-Trader 测试套件")
    print("="*80)
    
    # 发现所有测试
    loader = unittest.TestLoader()
    test_dir = project_root / 'tests'
    suite = loader.discover(test_dir, pattern='test_*.py')
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*80)
    print("测试总结:")
    print("-"*80)
    print(f"运行测试:  {result.testsRun}")
    print(f"成功:      {result.testsRun - len(result.failures) - len(result.errors)} ✅")
    print(f"失败:      {len(result.failures)} ❌")
    print(f"错误:      {len(result.errors)} ⚠️")
    print(f"跳过:      {len(result.skipped)} ⏭️")
    print("="*80)
    
    # 打印失败详情
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback[:200]}...")
    
    # 打印错误详情
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback[:200]}...")
    
    return result.wasSuccessful()


def run_specific_test(test_module, verbosity=2):
    """运行特定测试模块
    
    Args:
        test_module: 测试模块名（不含.py）
        verbosity: 详细程度
    
    Returns:
        bool: 测试是否通过
    """
    print(f"运行测试模块: {test_module}")
    print("="*60)
    
    # 导入测试模块
    module = __import__(f'tests.{test_module}', fromlist=[test_module])
    
    # 运行测试
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module)
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='运行AI-Trader测试套件')
    parser.add_argument('--module', '-m', type=str, default=None,
                       help='指定测试模块（例如：test_astock_data）')
    parser.add_argument('--verbosity', '-v', type=int, default=2, choices=[0, 1, 2],
                       help='输出详细程度 (0=静默, 1=正常, 2=详细)')
    parser.add_argument('--list', '-l', action='store_true',
                       help='列出所有可用的测试模块')
    
    args = parser.parse_args()
    
    # 列出测试模块
    if args.list:
        print("可用的测试模块:")
        test_dir = project_root / 'tests'
        for test_file in test_dir.glob('test_*.py'):
            print(f"  - {test_file.stem}")
        return 0
    
    # 运行测试
    if args.module:
        success = run_specific_test(args.module, verbosity=args.verbosity)
    else:
        success = run_all_tests(verbosity=args.verbosity)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
