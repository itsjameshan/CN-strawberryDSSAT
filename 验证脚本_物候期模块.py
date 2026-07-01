# -*- coding: utf-8 -*-
"""
物候期判定模块验证脚本
=================

本脚本用于验证草莓模型的物候期判定模块（PHENOL）的正确性。
包括以下物候阶段的测试：
- GERMINATION (发芽期)
- EMERGENCE (出苗期)
- VEGETATIVE (营养生长期)
- FLOWERING (开花期)
- FRUITING (结果期)
- MATURITY (成熟期)
- SENESCENCE (衰老期)

验证方法：
1. 使用标准气象数据输入
2. 检查各物候阶段转换的日期
3. 对比预期结果与实际结果

作者：代码验证组
日期：2026-06-30
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cropgro_strawberry_implementation import (
    CropgroStrawberry,
    PlantState,
    _thermal_time,
    _calc_daylength
)


class PhenologyValidator:
    """物候期验证器类"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def log_result(self, test_name, passed, expected, actual, message=""):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'expected': str(expected),
            'actual': str(actual),
            'message': message
        }
        self.test_results.append(result)
        if passed:
            self.passed += 1
            print(f"  ✅ {test_name}: PASS")
        else:
            self.failed += 1
            print(f"  ❌ {test_name}: FAIL")
            print(f"     预期: {expected}")
            print(f"     实际: {actual}")
            if message:
                print(f"     说明: {message}")
    
    def test_thermal_time_calculation(self):
        """测试积温计算"""
        print("\n--- 测试积温计算 ---")
        
        # 测试用例1：正常温度范围
        tt = _thermal_time(tmin=15, tmax=25, tbase=4, topt=22, tmax_th=35)
        expected_range = (8, 12)  # 积温应该在8-12度·天之间
        passed = expected_range[0] <= tt <= expected_range[1]
        self.log_result("正常温度范围积温", passed, f"{expected_range[0]}-{expected_range[1]}", f"{tt:.2f}")
        
        # 测试用例2：低温条件（低于基温）
        tt_low = _thermal_time(tmin=0, tmax=3, tbase=4, topt=22, tmax_th=35)
        self.log_result("低温条件积温为0", tt_low == 0, 0, tt_low)
        
        # 测试用例3：高温条件（超过最适温）
        tt_high = _thermal_time(tmin=25, tmax=38, tbase=4, topt=22, tmax_th=35)
        passed = tt_high < (22 - 4)  # 应该小于最适积温
        self.log_result("高温条件下积温减少", passed, f"<{22-4}", f"{tt_high:.2f}")
    
    def test_daylength_calculation(self):
        """测试日照长度计算"""
        print("\n--- 测试日照长度计算 ---")
        
        # 赤道处，春分秋分（DOY=80, 172）日照约12小时
        dl_equator = _calc_daylength(latitude=0, day_of_year=80)
        passed = 11.5 <= dl_equator <= 12.5
        self.log_result("赤道处日照长度", passed, "约12小时", f"{dl_equator:.2f}小时")
        
        # 北纬30度，夏季（DOY=172）日照约14小时
        dl_summer = _calc_daylength(latitude=30, day_of_year=172)
        passed = 13.5 <= dl_summer <= 14.5
        self.log_result("北纬30度夏季日照", passed, "约14小时", f"{dl_summer:.2f}小时")
        
        # 北纬60度，冬季（DOY=355）日照很短
        dl_winter = _calc_daylength(latitude=60, day_of_year=355)
        passed = 5 <= dl_winter <= 7
        self.log_result("北纬60度冬季日照", passed, "约5-7小时", f"{dl_winter:.2f}小时")
    
    def test_phenological_stages(self):
        """测试物候阶段定义"""
        print("\n--- 测试物候阶段定义 ---")
        
        # 创建模型实例
        soil_props = {
            'max_root_depth': 50.0,
            'field_capacity': 200.0,
            'wilting_point': 50.0
        }
        cultivar = {
            'name': 'Albion',
            'tbase': 4.0,
            'topt': 22.0,
            'tmax_th': 35.0,
            'rue': 2.5,
            'k_light': 0.6,
            'sla': 0.02,
            'potential_fruits_per_crown': 10.0
        }
        
        model = CropgroStrawberry(
            latitude=-12.97,  # 巴西萨尔瓦多
            planting_date='2023-05-01',
            soil_properties=soil_props,
            cultivar_params=cultivar
        )
        
        # 检查初始状态
        expected_stage = "GERMINATION"
        passed = model.state.phenological_stage == expected_stage
        self.log_result("初始物候阶段", passed, expected_stage, 
                       model.state.phenological_stage)
        
        # 检查物候阶段列表
        expected_stages = ['GERMINATION', 'EMERGENCE', 'VEGETATIVE', 
                          'FLOWERING', 'FRUITING', 'MATURITY', 'SENESCENCE']
        actual_stages = list(model.phenology_stages.keys())
        passed = actual_stages == expected_stages
        self.log_result("物候阶段列表", passed, expected_stages, actual_stages)
    
    def test_stage_transitions(self):
        """测试物候阶段转换"""
        print("\n--- 测试物候阶段转换 ---")
        
        # 创建模型实例
        soil_props = {
            'max_root_depth': 50.0,
            'field_capacity': 200.0,
            'wilting_point': 50.0
        }
        cultivar = {
            'name': 'Albion',
            'tbase': 4.0,
            'topt': 22.0,
            'tmax_th': 35.0,
            'rue': 2.5,
            'k_light': 0.6,
            'sla': 0.02,
            'potential_fruits_per_crown': 10.0
        }
        
        model = CropgroStrawberry(
            latitude=-12.97,
            planting_date='2023-05-01',
            soil_properties=soil_props,
            cultivar_params=cultivar
        )
        
        # 生成一个生长季的气象数据
        n_days = 180
        dates = pd.date_range(start='2023-05-01', periods=n_days)
        
        np.random.seed(42)
        doy = np.array([d.timetuple().tm_yday for d in dates])
        seasonal = 10 * np.sin(2 * np.pi * (doy - 172) / 365)
        
        weather_df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in dates],
            'tmax': 25 + seasonal + np.random.normal(0, 3, n_days),
            'tmin': 10 + seasonal + np.random.normal(0, 2, n_days),
            'solar_radiation': 15 + 10 * np.sin(2 * np.pi * (doy - 172) / 365) + np.random.normal(0, 2, n_days),
            'rainfall': np.where(np.random.rand(n_days) < 0.3, np.random.exponential(5, n_days), 0),
            'rh': np.clip(70 + np.random.normal(0, 10, n_days), 20, 100),
            'wind_speed': 2 + np.random.exponential(1, n_days)
        })
        
        # 运行模拟
        model.simulate_growth(weather_df)
        
        # 获取结果
        results = model.results_df
        
        # 检查是否有多个物候阶段
        unique_stages = results['stage'].unique()
        passed = len(unique_stages) >= 3  # 至少应该经历3个阶段
        self.log_result("物候阶段多样性", passed, ">=3个阶段", 
                       f"{len(unique_stages)}个阶段: {list(unique_stages)}")
        
        # 检查最终阶段
        final_stage = results['stage'].iloc[-1]
        expected_final = 'SENESCENCE'
        passed = final_stage == expected_final
        self.log_result("最终物候阶段", passed, expected_final, final_stage)
        
        # 打印阶段转换信息
        print(f"\n  物候阶段转换记录:")
        prev_stage = None
        for idx, row in results.iterrows():
            if row['stage'] != prev_stage:
                print(f"    第{row['dap']}天: {row['stage']}")
                prev_stage = row['stage']
    
    def test_phenology_timing(self):
        """测试物候时间节点"""
        print("\n--- 测试物候时间节点 ---")
        
        # 创建模型实例
        soil_props = {
            'max_root_depth': 50.0,
            'field_capacity': 200.0,
            'wilting_point': 50.0
        }
        cultivar = {
            'name': 'Albion',
            'tbase': 4.0,
            'topt': 22.0,
            'tmax_th': 35.0,
            'rue': 2.5,
            'k_light': 0.6,
            'sla': 0.02,
            'potential_fruits_per_crown': 10.0
        }
        
        model = CropgroStrawberry(
            latitude=-12.97,
            planting_date='2023-05-01',
            soil_properties=soil_props,
            cultivar_params=cultivar
        )
        
        # 生成气象数据
        n_days = 180
        dates = pd.date_range(start='2023-05-01', periods=n_days)
        
        np.random.seed(42)
        doy = np.array([d.timetuple().tm_yday for d in dates])
        seasonal = 10 * np.sin(2 * np.pi * (doy - 172) / 365)
        
        weather_df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in dates],
            'tmax': 25 + seasonal + np.random.normal(0, 3, n_days),
            'tmin': 10 + seasonal + np.random.normal(0, 2, n_days),
            'solar_radiation': 15 + 10 * np.sin(2 * np.pi * (doy - 172) / 365) + np.random.normal(0, 2, n_days),
            'rainfall': np.where(np.random.rand(n_days) < 0.3, np.random.exponential(5, n_days), 0),
            'rh': np.clip(70 + np.random.normal(0, 10, n_days), 20, 100),
            'wind_speed': 2 + np.random.exponential(1, n_days)
        })
        
        # 运行模拟
        model.simulate_growth(weather_df)
        results = model.results_df
        
        # 记录各阶段出现的天数
        stage_days = {}
        for stage in results['stage'].unique():
            stage_df = results[results['stage'] == stage]
            stage_days[stage] = stage_df['dap'].iloc[0]
        
        print(f"\n  各物候阶段首次出现天数:")
        for stage, day in sorted(stage_days.items(), key=lambda x: x[1]):
            print(f"    {stage}: 第{day}天")
        
        # 验证开花期应该在结果期之前
        if 'FLOWERING' in stage_days and 'FRUITING' in stage_days:
            passed = stage_days['FLOWERING'] < stage_days['FRUITING']
            self.log_result("开花期在结果期之前", passed, 
                           f"开花<结果", 
                           f"开花={stage_days['FLOWERING']}, 结果={stage_days['FRUITING']}")
        
        # 验证结果期应该在成熟期之前
        if 'FRUITING' in stage_days and 'MATURITY' in stage_days:
            passed = stage_days['FRUITING'] < stage_days['MATURITY']
            self.log_result("结果期在成熟期之前", passed,
                           f"结果<成熟",
                           f"结果={stage_days['FRUITING']}, 成熟={stage_days['MATURITY']}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("物候期判定模块（PHENOL）验证测试")
        print("=" * 60)
        
        self.test_thermal_time_calculation()
        self.test_daylength_calculation()
        self.test_phenological_stages()
        self.test_stage_transitions()
        self.test_phenology_timing()
        
        print("\n" + "=" * 60)
        print(f"测试完成: {self.passed} 通过, {self.failed} 失败")
        print("=" * 60)
        
        return self.failed == 0
    
    def generate_report(self):
        """生成测试报告"""
        report = []
        report.append("# 物候期模块验证报告\n")
        report.append(f"**测试日期**: 2026-06-30\n")
        report.append(f"**测试结果**: {'全部通过' if self.failed == 0 else f'{self.failed}项失败'}\n")
        report.append(f"**通过率**: {self.passed}/{self.passed + self.failed}\n\n")
        
        report.append("## 详细结果\n")
        report.append("| 测试名称 | 结果 | 预期值 | 实际值 | 说明 |\n")
        report.append("|---------|------|--------|--------|------|\n")
        
        for result in self.test_results:
            status = "✅ 通过" if result['passed'] else "❌ 失败"
            report.append(f"| {result['test_name']} | {status} | {result['expected']} | {result['actual']} | {result['message']} |\n")
        
        return "".join(report)


def main():
    """主函数"""
    validator = PhenologyValidator()
    
    success = validator.run_all_tests()
    
    # 生成报告
    report = validator.generate_report()
    print("\n" + report)
    
    # 保存报告
    report_path = r"D:\编程\物候期模块验证报告.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存至: {report_path}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
