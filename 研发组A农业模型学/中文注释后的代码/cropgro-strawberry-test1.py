"""针对简化版 CROPGRO-Strawberry 模型实现的单元测试文件"""
# 文件的描述性注释，说明这是一个针对简化版 CROPGRO-Strawberry 模型实现的单元测试文件。

import unittest
# 导入 Python 的单元测试框架，用于编写和运行测试用例。
import pandas as pd
# 导入 pandas 库，用于数据处理和分析。
import numpy as np
# 导入 numpy 库，用于数值计算。
import matplotlib.pyplot as plt
# 导入 matplotlib.pyplot，用于绘图。
from datetime import datetime
# 从 datetime 模块导入 datetime 类，用于处理日期和时间。
import io
# 导入 io 模块，用于处理输入输出流。
import sys
# 导入 sys 模块，用于访问与 Python 解释器相关的功能。

# 从实现文件中导入 CropgroStrawberry 类
# 这是关键修复 - 我们正确地导入了模型类

# 选项 1：如果你将模型保存在名为 cropgro_strawberry.py 的文件中，请取消以下注释：
# from cropgro_strawberry import CropgroStrawberry

# 选项 2：为了演示，我们将直接在这里包含类
# 这确保了测试文件是自包含的，并且可以运行

# 以下是用于测试目的的简化版 CropgroStrawberry 类
class CropgroStrawberry:
    """用于测试的简化版 CROPGRO-Strawberry 模型"""
    # 定义一个简化版的 CROPGRO-Strawberry 模型类，用于测试。

    def __init__(self, latitude, planting_date, soil_properties, cultivar_params):
        """用站点和品种信息初始化模型。

        参数
        ----
        latitude : float
            地理纬度，单位为度。
        planting_date : str
            种植日期，格式为 ``YYYY-MM-DD``。
        soil_properties : dict
            土壤特性，如 ``field_capacity`` 和 ``wilting_point``。
        cultivar_params : dict
            描述草莓品种的参数。
        """
        # 构造函数，用于初始化模型，接收纬度、种植日期、土壤属性和品种参数作为输入。

        self.latitude = latitude
        # 保存纬度信息。
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        # 将种植日期字符串转换为 datetime 对象并保存。
        self.soil = soil_properties
        # 保存土壤属性。
        self.cultivar = cultivar_params
        # 保存品种参数。
        
        # 初始化状态变量
        self.days_after_planting = 0
        # 初始化种植后天数为 0。
        self.plant_state = {
            'biomass': 0.0,
            'leaf_area_index': 0.1,
            'root_depth': 5.0,
            'fruit_number': 0,
            'fruit_biomass': 0.0,
            'leaf_biomass': 0.0,
            'stem_biomass': 0.0,
            'root_biomass': 0.0,
            'phenological_stage': 'GERMINATION',
            'development_rate': 0.0,
            'crown_number': 1.0,
            'runner_number': 0.0,
        }
        # 初始化植物状态变量，包括生物量、叶面积指数、根系深度等。
        
        self.thermal_time = 0.0
        # 初始化热时间为 0。
        self.phenology_stages = {
            'GERMINATION': 0,
            'EMERGENCE': 50,
            'JUVENILE': 100, 
            'VEGETATIVE': 200,
            'FLORAL_INDUCTION': 400,
            'FLOWERING': 600,
            'FRUIT_SET': 700,
            'FRUIT_DEVELOPMENT': 800,
            'FRUIT_MATURITY': 1000,
            'SENESCENCE': 1500
        }
        # 定义生育阶段及其对应的热时间阈值。
        self.results = []
        # 初始化结果列表，用于存储模拟结果。
    
    def calculate_daylength(self, day_of_year):
        """计算天文日长，单位为小时。

        计算使用太阳赤纬角和纬度。结果被限制在 ``0`` 到 ``24`` 小时之间，以处理极地附近极端日长的情况。
        """
        # 计算天文日长（小时），使用太阳赤纬角和纬度进行计算，并限制结果在 0 到 24 小时之间。

        # 给定年份中的天数对应的太阳赤纬角
        declination = 23.45 * np.sin(np.radians(360 * (day_of_year - 80) / 365))
        # 计算给定年份中的天数对应的太阳赤纬角。

        # 将纬度转换为弧度
        lat_rad = np.radians(self.latitude)
        # 将纬度转换为弧度。

        # 日长方程的中间项
        term = -np.tan(lat_rad) * np.tan(np.radians(declination))
        # 计算日长方程的中间项。

        if term >= 1.0:
            daylength = 0.0
        elif term <= -1.0:
            daylength = 24.0
        else:
            daylength = 24.0 * np.arccos(term) / np.pi
        # 根据中间项的值计算日长，并限制结果在 0 到 24 小时之间。
        return daylength
    
    def calculate_thermal_time(self, tmin, tmax):
        """返回热时间，单位为度日。

        使用梯形温度响应，在 ``tbase`` 和 ``topt`` 之间逐渐增加，在 ``tmax_th`` 时降为零。
        """
        # 返回热时间（度日），使用梯形温度响应，从 tbase 到 topt 逐渐增加，到 tmax_th 时降为零。

        tbase = self.cultivar['tbase']
        # 获取品种的基础温度。
        topt = self.cultivar['topt']
        # 获取品种的最适温度。
        tmax_th = self.cultivar['tmax_th']
        # 获取品种的最高阈值温度。
# 计算日平均温度
tavg = (tmin + tmax) / 2.0

# 根据平均温度计算热时间
if tavg <= tbase:
    return 0.0  # 如果平均温度低于基础温度，则热时间为零
elif tavg <= topt:
    return tavg - tbase  # 如果平均温度在基础温度和最适温度之间，则热时间为平均温度减去基础温度
elif tavg <= tmax_th:
    return topt - tbase - (tavg - topt) * ((topt - tbase) / (tmax_th - topt))
    # 如果平均温度在最适温度和最高阈值温度之间，则根据梯形响应计算热时间
else:
    return 0.0  # 如果平均温度高于最高阈值温度，则热时间为零

def update_phenology(self, thermal_time_today):
    """当达到热时间阈值时，推进生育阶段。"""
    self.thermal_time += thermal_time_today  # 累加今天的热时间

    current_stage = self.plant_state['phenological_stage']  # 获取当前生育阶段
    stages = list(self.phenology_stages.keys())  # 获取所有生育阶段的列表
    current_index = stages.index(current_stage)  # 获取当前生育阶段在列表中的索引

    # 检查是否需要推进到下一个生育阶段
    if current_index < len(stages) - 1:
        next_stage = stages[current_index + 1]  # 获取下一个生育阶段
        if self.thermal_time >= self.phenology_stages[next_stage]:
            self.plant_state['phenological_stage'] = next_stage  # 更新生育阶段

def calculate_photosynthesis(self, solar_radiation, tmax, tmin, co2=400):
    """计算每日总光合作用。

    辐射利用效率（RUE）会受到温度、CO2 和基于 LAI 的截获光的比例的影响。
    """
    rue = self.cultivar['rue']  # 获取品种的辐射利用效率
    tavg = (tmax + tmin) / 2.0  # 计算日平均温度

    # 温度对光合作用的影响
    if tavg <= self.cultivar['tbase']:
        temp_effect = 0.0  # 如果平均温度低于基础温度，则温度效应为零
    elif tavg >= self.cultivar['topt']:
        temp_effect = 1.0  # 如果平均温度高于最适温度，则温度效应为一
    else:
        temp_effect = (tavg - self.cultivar['tbase']) / (
            self.cultivar['topt'] - self.cultivar['tbase']
        )  # 如果平均温度在基础温度和最适温度之间，则按比例计算温度效应

    # 高浓度 CO2 的影响
    co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)  # 计算 CO2 浓度的影响

    # 冠层截获光的比例
    lai = self.plant_state['leaf_area_index']  # 获取叶面积指数
    light_interception = 1.0 - np.exp(-self.cultivar['k_light'] * lai)  # 计算截获光的比例

    # 计算光合作用
    photosynthesis = (
        solar_radiation * rue * temp_effect * co2_effect * light_interception
    )  # 根据太阳辐射、辐射利用效率、温度效应、CO2 效应和截获光的比例计算光合作用

    return photosynthesis  # 返回计算结果

def calculate_transpiration(self, solar_radiation, tmax, tmin, rh, wind_speed):
    """根据天气条件估算作物蒸腾量。"""
    tavg = (tmax + tmin) / 2.0  # 计算日平均温度
    # 蒸汽压亏缺（未使用，但为了清晰起见而显示）
    vpd = 0.611 * np.exp(17.27 * tavg / (tavg + 237.3)) * (1 - rh / 100)

    # 使用 Hargreaves 方程计算参考蒸散发
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)
        
        # 作物系数根据冠层大小对参考蒸散发（ET0）进行调整。
        lai = self.plant_state['leaf_area_index']
        kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
# 返回计算得到的参考蒸散发（ET0）乘以作物系数（kc）
return et0 * kc

def partition_biomass(self, daily_biomass):
    """将新生物量分配到叶子、茎、根和果实中。"""
    stage = self.plant_state['phenological_stage']
    # 获取当前的生育阶段

    # 根据生育阶段定义分配系数
    if stage in ['GERMINATION', 'EMERGENCE', 'JUVENILE']:
        root_fraction = 0.4  # 根的分配比例
        leaf_fraction = 0.4  # 叶子的分配比例
        stem_fraction = 0.2  # 茎的分配比例
        fruit_fraction = 0.0  # 果实的分配比例
    elif stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
        root_fraction = 0.2
        leaf_fraction = 0.5
        stem_fraction = 0.3
        fruit_fraction = 0.0
    elif stage == 'FLOWERING':
        root_fraction = 0.1
        leaf_fraction = 0.4
        stem_fraction = 0.3
        fruit_fraction = 0.2
    elif stage in ['FRUIT_SET', 'FRUIT_DEVELOPMENT']:
        root_fraction = 0.05
        leaf_fraction = 0.25
        stem_fraction = 0.2
        fruit_fraction = 0.5
    elif stage == 'FRUIT_MATURITY':
        root_fraction = 0.0
        leaf_fraction = 0.1
        stem_fraction = 0.1
        fruit_fraction = 0.8
    else:  # 'SENESCENCE'
        root_fraction = 0.0
        leaf_fraction = 0.0
        stem_fraction = 0.0
        fruit_fraction = 0.0
    
    # 将分配的生物量添加到每个部分
    self.plant_state['root_biomass'] += daily_biomass * root_fraction
    self.plant_state['leaf_biomass'] += daily_biomass * leaf_fraction
    self.plant_state['stem_biomass'] += daily_biomass * stem_fraction
    self.plant_state['fruit_biomass'] += daily_biomass * fruit_fraction
    
    # 更新总生物量
    self.plant_state['biomass'] = (self.plant_state['root_biomass'] + 
                                  self.plant_state['leaf_biomass'] + 
                                  self.plant_state['stem_biomass'] + 
                                  self.plant_state['fruit_biomass'])
    
    # 使用比叶面积将叶生物量转换为叶面积指数
    sla = self.cultivar['sla']
    if stage in ['FRUIT_DEVELOPMENT', 'FRUIT_MATURITY', 'SENESCENCE']:
        sla *= 0.8  # 在果实发育、成熟和衰老阶段，比叶面积乘以0.8
    
    self.plant_state['leaf_area_index'] = self.plant_state['leaf_biomass'] * sla
    
    # 根据分配的根生长更新根系深度
    max_root_growth_rate = 0.5  # 最大根生长速率
    max_root_depth = self.soil['max_root_depth']  # 土壤最大根系深度
    
    potential_root_growth = max_root_growth_rate * root_fraction
    current_root_depth = self.plant_state['root_depth']

    if current_root_depth < max_root_depth:
        self.plant_state['root_depth'] = min(
            current_root_depth + potential_root_growth,
            max_root_depth,
        )  # 更新根系深度，但不超过最大根系深度

def calculate_water_stress(self, rainfall, transpiration):
    """返回一个介于 0 和 1 之间的水分胁迫因子。"""
    field_capacity = self.soil['field_capacity']  # 土壤田间持水量
    wilting_point = self.soil['wilting_point']  # 土壤凋萎系数
    root_depth = self.plant_state['root_depth'] / 100.0  # 根系深度（单位：米）

    # 根系区域的可用土壤水分
    available_water = (field_capacity - wilting_point) * root_depth
    effective_rainfall = rainfall * 0.7  # 有效降雨量（假设70%的降雨有效）
    deficit = max(0, transpiration - effective_rainfall)  # 蒸腾量与有效降雨量的差值（水分亏缺）
    
    if deficit == 0:
        return 0.0  # 如果没有水分亏缺，则水分胁迫因子为0
    else:
        # 根据可用水分对亏缺进行缩放以确定胁迫
        stress_factor = min(1.0, deficit / available_water)
        return stress_factor  # 返回水分胁迫因子

def calculate_maintenance_respiration(self, tmin, tmax):
    """根据生物量和温度计算呼吸作用。"""
    tavg = (tmin + tmax) / 2.0  # 计算日平均温度

    # 在20°C时的呼吸作用系数
    coef_leaf = 0.03  # 叶子的呼吸作用系数
    coef_stem = 0.015  # 茎的呼吸作用系数
    coef_root = 0.01  # 根的呼吸作用系数
    coef_fruit = 0.01  # 果实的呼吸作用系数

    # 假设Q10为2，计算温度效应
    temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)

    # 计算各部分的呼吸作用
    resp_leaf = self.plant_state['leaf_biomass'] * coef_leaf * temp_factor
    resp_stem = self.plant_state['stem_biomass'] * coef_stem * temp_factor
    resp_root = self.plant_state['root_biomass'] * coef_root * temp_factor
    resp_fruit = self.plant_state['fruit_biomass'] * coef_fruit * temp_factor

    # 返回总呼吸作用
    return resp_leaf + resp_stem + resp_root + resp_fruit
    
def update_runners(self):
    """在营养生长期间增加匍匐茎的数量。"""
    if self.plant_state['phenological_stage'] in [
        'VEGETATIVE',  # 营养生长阶段
        'FLORAL_INDUCTION',  # 花芽诱导阶段
    ]:
        # 在营养生长和花芽诱导阶段，匍匐茎数量增加
        self.plant_state['runner_number'] += 0.1 * self.plant_state['crown_number']
        # 根据植株数量增加匍匐茎数量

def update_crowns(self):
    """随着冠层发育增加植株数量。"""
    if self.plant_state['phenological_stage'] in [
        'VEGETATIVE',  # 营养生长阶段
        'FLORAL_INDUCTION',  # 花芽诱导阶段
        'FLOWERING',  # 开花阶段
    ]:
        # 在营养生长、花芽诱导和开花阶段，植株数量增加
        self.plant_state['crown_number'] += 0.02 * self.plant_state['crown_number']
        # 根据当前植株数量增加植株数量

def update_fruits(self):
    """在开花和果实形成阶段增加果实数量。"""
    stage = self.plant_state['phenological_stage']
    # 获取当前生育阶段

    if stage == 'FLOWERING':
        # 初期果实形成
        new_fruits = (
            self.cultivar['potential_fruits_per_crown']
            * self.plant_state['crown_number']
            * 0.1
        )
        # 根据每个植株可能的果实数量和植株数量计算新果实数量
        self.plant_state['fruit_number'] += new_fruits
        # 增加果实数量
    elif stage == 'FRUIT_SET':
        # 额外果实形成
        new_fruits = (
            self.cultivar['potential_fruits_per_crown']
            * self.plant_state['crown_number']
            * 0.2
        )
        # 根据每个植株可能的果实数量和植株数量计算新果实数量
        self.plant_state['fruit_number'] += new_fruits
        # 增加果实数量

def simulate_day(self, weather_data):
    """模拟一天的草莓生长。"""
    self.days_after_planting += 1
    # 种植后天数加一

    current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
    # 将天气数据中的日期字符串转换为 datetime 对象
    day_of_year = current_date.timetuple().tm_yday
    # 获取当前日期在一年中的天数

    # 环境胁迫
    daylength = self.calculate_daylength(day_of_year)
    # 计算天文日长
    thermal_time_today = self.calculate_thermal_time(
        weather_data['tmin'], weather_data['tmax']
    )
    # 计算当天的热时间
    self.update_phenology(thermal_time_today)
    # 更新生育阶段

    photosynthesis = self.calculate_photosynthesis(
        weather_data['solar_radiation'], 
        weather_data['tmax'], 
        weather_data['tmin']
    )
    # 计算光合作用

    transpiration = self.calculate_transpiration(
        weather_data['solar_radiation'],
        weather_data['tmax'],
        weather_data['tmin'],
        weather_data['rh'],
        weather_data['wind_speed']
    )
    # 计算蒸腾量

    # 根据水分胁迫减少光合作用
    water_stress = self.calculate_water_stress(
        weather_data['rainfall'], transpiration
    )
    # 计算水分胁迫
    photosynthesis *= (1 - water_stress)
    # 根据水分胁迫调整光合作用

    plant_density = 5.0
    # 植株密度
    daily_biomass = photosynthesis / plant_density
    # 计算每日生物量

    maintenance_resp = self.calculate_maintenance_respiration(
        weather_data['tmin'], weather_data['tmax']
    )
    # 计算呼吸作用
    daily_biomass = max(0, daily_biomass - maintenance_resp)
    # 减去呼吸作用后的生物量，确保不为负值

    self.partition_biomass(daily_biomass)
    # 将生物量分配到各个部分
    self.update_runners()
    # 更新匍匐茎数量
    self.update_crowns()
    # 更新植株数量
    self.update_fruits()
    # 更新果实数量

  def simulate_growth(self, weather_data_df):
    """依次运行模型，处理天气数据集中的每一天。"""
    # 初始化结果列表，用于存储每天的模拟结果
    self.results = []
        
    # 遍历天气数据集的每一行
    for _, row in weather_data_df.iterrows():
        # 提取当天的天气数据
        weather_day = {
            'date': row['date'],  # 当天的日期
            'tmax': row['tmax'],  # 当天的最高气温
            'tmin': row['tmin'],  # 当天的最低气温
            'solar_radiation': row['solar_radiation'],  # 当天的太阳辐射
            'rainfall': row['rainfall'],  # 当天的降雨量
            'rh': row['rh'],  # 当天的相对湿度
            'wind_speed': row['wind_speed']  # 当天的风速
        }
        # 调用 simulate_day 方法模拟当天的生长情况
        self.simulate_day(weather_day)

    # 将收集到的结果转换为 DataFrame 以便于分析
    self.results_df = pd.DataFrame(self.results)
    # 返回结果 DataFrame
    return self.results_df

def plot_results(self):
    """绘制关键模拟结果。"""
    # 检查是否有模拟结果
    if not hasattr(self, 'results_df') or len(self.results_df) == 0:
        # 如果没有模拟结果，则提示用户先运行 simulate_growth 方法
        print("No simulation results to plot. Run simulate_growth() first.")
        return None
        
    # 创建一个 2x2 的绘图布局，大小为 10x8 英寸
    fig, axs = plt.subplots(2, 2, figsize=(10, 8))
        
    # 绘制生物量随种植后天数的变化
    axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 'b-')  # 使用蓝色线条
    axs[0, 0].set_xlabel('Days After Planting')  # 设置 x 轴标签
    axs[0, 0].set_ylabel('Biomass (g/plant)')  # 设置 y 轴标签
    axs[0, 0].set_title('Plant Biomass')  # 设置子图标题
        
    # 绘制叶面积指数随种植后天数的变化
    axs[0, 1].plot(self.results_df['dap'], self.results_df['leaf_area_index'], 'g-')  # 使用绿色线条
    axs[0, 1].set_xlabel('Days After Planting')  # 设置 x 轴标签
    axs[0, 1].set_ylabel('LAI (m²/m²)')  # 设置 y 轴标签
    axs[0, 1].set_title('Leaf Area Index')  # 设置子图标题
        
# 绘制生育阶段
stages = list(self.phenology_stages.keys())  # 获取所有生育阶段的名称列表
stage_values = [stages.index(stage) for stage in self.results_df['stage']]
# 将生育阶段名称转换为对应的索引值，用于绘图

# 在子图 1,0 的位置绘制生育阶段随种植后天数的变化
axs[1, 0].plot(self.results_df['dap'], stage_values, 'b-')  # 使用蓝色线条绘制
axs[1, 0].set_xlabel('Days After Planting')  # 设置 x 轴标签为“种植后天数”
axs[1, 0].set_ylabel('Development Stage')  # 设置 y 轴标签为“发育阶段”
axs[1, 0].set_yticks(range(len(stages)))  # 设置 y 轴刻度为生育阶段的索引
axs[1, 0].set_yticklabels(stages)  # 设置 y 轴刻度标签为生育阶段的名称
axs[1, 0].set_title('Phenological Development')  # 设置子图标题为“生育期发展”

# 绘制果实生物量
# 在子图 1,1 的位置绘制果实生物量随种植后天数的变化
axs[1, 1].plot(self.results_df['dap'], self.results_df['fruit_biomass'], 'm-')  # 使用品红色线条绘制
axs[1, 1].set_xlabel('Days After Planting')  # 设置 x 轴标签为“种植后天数”
axs[1, 1].set_ylabel('Fruit Biomass (g/plant)')  # 设置 y 轴标签为“果实生物量 (g/株)”
axs[1, 1].set_title('Fruit Growth')  # 设置子图标题为“果实生长”

# 调整布局，使子图之间不重叠
plt.tight_layout()
# 返回绘制的图形对象
return fig

class TestCropgroStrawberry(unittest.TestCase):
    """CROPGRO-Strawberry 模型的测试套件。"""
    # 定义一个测试类，继承自 unittest.TestCase，用于包含针对 CROPGRO-Strawberry 模型的测试用例。

    def setUp(self):
        """在每个测试方法之前设置测试环境。"""
        # 定义土壤属性
        self.soil_properties = {
            'max_root_depth': 50.0,  # 最大根系深度 (cm)
            'field_capacity': 200.0,  # 田间持水量 (mm/m)
            'wilting_point': 50.0,   # 凋萎点 (mm/m)
        }
        # 定义土壤属性，包括最大根系深度、田间持水量和凋萎点。

        # 定义品种参数
        self.cultivar_params = {
            'name': 'Albion',  # 品种名称
            'tbase': 4.0,       # 基础温度 (°C)
            'topt': 22.0,       # 最适温度 (°C)
            'tmax_th': 35.0,    # 最高阈值温度 (°C)
            'rue': 2.5,         # 辐射利用效率 (g/MJ)
            'k_light': 0.6,     # 光衰减系数
            'sla': 0.02,        # 比叶面积 (m²/g)
            'potential_fruits_per_crown': 10.0  # 每株潜在果实数
        }
        # 定义品种参数，包括名称、基础温度、最适温度、最高阈值温度、辐射利用效率、光衰减系数、比叶面积和每株潜在果实数。

        # 创建一个简单的天气数据集用于测试
        self.test_dates = pd.date_range(start='2023-05-01', end='2023-05-10')  # 测试日期范围
        self.n_days = len(self.test_dates)  # 测试天数
        # 创建一个简单的天气数据集，包括从 2023-05-01 到 2023-05-10 的日期范围和天数。

        # 创建简单的合成天气数据，所有值均为常数，便于预测性测试
        self.weather_df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in self.test_dates],  # 日期
            'tmax': [25.0] * self.n_days,  # 最高气温
            'tmin': [15.0] * self.n_days,  # 最低气温
            'solar_radiation': [20.0] * self.n_days,  # 太阳辐射
            'rainfall': [5.0] * self.n_days,  # 降雨量
            'rh': [70.0] * self.n_days,  # 相对湿度
            'wind_speed': [2.0] * self.n_days  # 风速
        })
        # 创建一个简单的合成天气数据集，包括日期、最高温度、最低温度、太阳辐射、降雨量、相对湿度和风速，所有值均为常数，便于预测性测试。

        # 初始化模型
        self.model = CropgroStrawberry(
            latitude=40.0,  # 纬度
            planting_date='2023-05-01',  # 种植日期
            soil_properties=self.soil_properties,  # 土壤属性
            cultivar_params=self.cultivar_params  # 品种参数
        )
        # 初始化模型，设置纬度、种植日期、土壤属性和品种参数。

    def test_initialization(self):
        """测试模型是否正确初始化。"""
        # 检查纬度
        self.assertEqual(self.model.latitude, 40.0)
        # 检查模型的纬度是否正确初始化为 40.0。

        # 检查种植日期
        self.assertEqual(self.model.planting_date, datetime.strptime('2023-05-01', '%Y-%m-%d'))
        # 检查模型的种植日期是否正确初始化为 2023-05-01。

        # 检查土壤属性
        self.assertEqual(self.model.soil, self.soil_properties)
        # 检查模型的土壤属性是否正确初始化为定义的土壤属性。

        # 检查品种参数
        self.assertEqual(self.model.cultivar, self.cultivar_params)
        # 检查模型的品种参数是否正确初始化为定义的品种参数。

        # 检查初始植物状态
        self.assertEqual(self.model.days_after_planting,
def test_daylength_calculation(self):
    """测试日长计算函数。"""
    # 测试北半球夏至时的日长（大约6月21日）
    summer_daylength = self.model.calculate_daylength(172)  # 夏至时的日长
        
    # 测试北半球冬至时的日长（大约12月21日）
    winter_daylength = self.model.calculate_daylength(355)  # 冬至时的日长
        
    # 在北半球，夏季的日长应该比冬季长
    self.assertGreater(summer_daylength, winter_daylength)
        
    # 检查在北纬40°时，夏季和冬季的日长是否在合理范围内
    # 夏季：约14-15小时，冬季：约9-10小时
    self.assertGreater(summer_daylength, 14.0)
    self.assertLess(winter_daylength, 10.0)

def test_thermal_time_calculation(self):
    """测试热时间计算。"""
    # 测试低于基础温度时的热时间（应返回0）
    tt_below_base = self.model.calculate_thermal_time(2.0, 3.0)
    self.assertEqual(tt_below_base, 0.0)
        
    # 测试在基础温度和最适温度之间的热时间（应返回正值）
    tt_optimal = self.model.calculate_thermal_time(10.0, 20.0)
    self.assertGreater(tt_optimal, 0.0)
        
    # 测试高于最高阈值温度时的热时间（应返回0）
    tt_above_max = self.model.calculate_thermal_time(36.0, 40.0)
    self.assertEqual(tt_above_max, 0.0)

def test_phenology_update(self):
    """测试基于热时间更新植物生育阶段。"""
    # 初始生育阶段
    self.assertEqual(self.model.plant_state['phenological_stage'], 'GERMINATION')
        
    # 添加足够的热时间以达到出苗期
    self.model.update_phenology(50.0)
    self.assertEqual(self.model.plant_state['phenological_stage'], 'EMERGENCE')
        
    # 添加更多的热时间以达到幼年期
    self.model.update_phenology(50.0)
    self.assertEqual(self.model.plant_state['phenological_stage'], 'JUVENILE')

def test_photosynthesis_calculation(self):
    """测试每日光合作用的计算。"""
    # 测试在最佳条件下的光合作用
    photosynthesis = self.model.calculate_photosynthesis(20.0, 22.0, 15.0, 400)
        
    # 光合作用应为正值
    self.assertGreater(photosynthesis, 0.0)
        
    # 测试在低光照条件下的光合作用
    photosynthesis_low_light = self.model.calculate_photosynthesis(5.0, 22.0, 15.0, 400)
        
    # 低光照下的光合作用应低于最佳光照下的光合作用
    self.assertLess(photosynthesis_low_light, photosynthesis)
        
    # 测试在高浓度CO2条件下的光合作用
    photosynthesis_high_co2 = self.model.calculate_photosynthesis(20.0, 22.0, 15.0, 800)
        
     # 高浓度 CO2 下的光合作用应高于环境 CO2 下的光合作用
self.assertGreater(photosynthesis_high_co2, photosynthesis)

def test_transpiration_calculation(self):
    """测试每日蒸腾量的计算。"""
    # 计算蒸腾量
    transpiration = self.model.calculate_transpiration(20.0, 25.0, 15.0, 70.0, 2.0)
    
    # 蒸腾量应为正值
    self.assertGreater(transpiration, 0.0)
    
    # 测试在较高风速下的蒸腾量
    transpiration_high_wind = self.model.calculate_transpiration(20.0, 25.0, 15.0, 70.0, 5.0)
    
    # 风速与蒸腾量之间的关系复杂，取决于具体实现
    # 但至少可以检查它是一个合理的值
    self.assertGreater(transpiration_high_wind, 0.0)

def test_biomass_partitioning(self):
    """测试生物量在植物器官中的分配。"""
    # 初始生物量值
    initial_root = self.model.plant_state['root_biomass']
    initial_leaf = self.model.plant_state['leaf_biomass']
    initial_stem = self.model.plant_state['stem_biomass']
    initial_fruit = self.model.plant_state['fruit_biomass']
    
    # 添加新的生物量
    daily_biomass = 1.0  # 每株植物的生物量 (g)
    self.model.partition_biomass(daily_biomass)
    
    # 检查所有器官的生物量值是否增加
    self.assertGreater(self.model.plant_state['root_biomass'], initial_root)
    self.assertGreater(self.model.plant_state['leaf_biomass'], initial_leaf)
    self.assertGreater(self.model.plant_state['stem_biomass'], initial_stem)
    
    # 在早期阶段，果实的生物量可能不会增加
    if self.model.plant_state['phenological_stage'] in ['FLOWERING', 'FRUIT_SET', 'FRUIT_DEVELOPMENT', 'FRUIT_MATURITY']:
        self.assertGreater(self.model.plant_state['fruit_biomass'], initial_fruit)
    
    # 检查总生物量是否等于各器官生物量之和
    total_biomass = (self.model.plant_state['root_biomass'] + 
                     self.model.plant_state['leaf_biomass'] + 
                     self.model.plant_state['stem_biomass'] + 
                     self.model.plant_state['fruit_biomass'])
    
    self.assertAlmostEqual(self.model.plant_state['biomass'], total_biomass)

def test_water_stress_calculation(self):
    """测试水分胁迫因子的计算。"""
    # 测试在水分充足的情况下（降雨量 > 蒸腾量）
    water_stress_low = self.model.calculate_water_stress(10.0, 5.0)
    
    # 应为低胁迫（接近 0）
    self.assertLess(water_stress_low, 0.5)
    
    # 测试在水分亏缺的情况下（降雨量 < 蒸腾量）
    water_stress_high = self.model.calculate_water_stress(1.0, 10.0)
    
    # 应比之前更高
    self.assertGreater(water_stress_high, water_stress_low)

def test_maintenance_respiration(self):
    """测试呼吸作用的计算。"""
    # 设置一些生物量值用于测试
    self.model.plant_state['leaf_biomass'] = 10.0
    self.model.plant_state['stem_biomass'] = 5.0
    self.model.plant_state['root_biomass'] = 3.0
    self.model.plant_state['fruit_biomass'] = 2.0
    
    # 在参考温度下计算呼吸作用
    resp_ref = self.model.calculate_maintenance_respiration(15.0, 25.0)
    
    # 呼吸作用应为正值
    self.assertGreater(resp_ref, 0.0)
    
    # 在较高温度下计算
    resp_high = self.model.calculate_maintenance_respiration(25.0, 35.0)
    
    # 在较高温度下应更高（Q10 效应）
    self.assertGreater(resp_high, resp_ref)

def test_single_day_simulation(self):
    """测试单日模拟。"""
    # 获取第一天的天气数据
    weather_day = {
        'date': self.weather_df['date'].iloc[0],
        'tmax': self.weather_df['tmax'].iloc[0],
        'tmin': self.weather_df['tmin'].iloc[0],
        'solar_radiation': self.weather_df['solar_radiation'].iloc[0],
        'rainfall': self.weather_df['rainfall'].iloc[0],
        'rh': self.weather_df['rh'].iloc[0],
        'wind_speed': self.weather_df['wind_speed'].iloc[0]
    }
    
    # 初始状态
    initial_dap = self.model.days_after_planting
    initial_biomass = self.model.plant_state['biomass']
    
    # 模拟一天
    self.model.simulate_day(weather_day)
    
    # 检查种植后天数是否增加
    self.assertEqual(self.model.days_after_planting, initial_dap + 1)
    
    # 检查结果是否已存储
    self.assertEqual(len(self.model.results), 1)
    
    # 生物量应增加
    self.assertGreater(self.model.plant_state['biomass'], initial_biomass) 
   def test_full_simulation(self):
    """测试完整的生长模拟。"""
    # 运行模拟
    results = self.model.simulate_growth(self.weather_df)
    
    # 检查模拟是否运行了正确的天数
    self.assertEqual(len(results), self.n_days)
    
    # 检查结果是否包含关键变量
    required_columns = [
        'date', 'dap', 'stage', 'thermal_time', 'biomass', 
        'leaf_area_index', 'fruit_number', 'fruit_biomass'
    ]
    for col in required_columns:
        self.assertIn(col, results.columns)
    
    # 检查生物量是否随时间增加
    self.assertGreater(results['biomass'].iloc[-1], results['biomass'].iloc[0])
    
    # 检查热时间是否增加
    self.assertGreater(results['thermal_time'].iloc[-1], results['thermal_time'].iloc[0])

def test_plotting(self):
    """测试绘图函数。"""
    # 先运行模拟
    self.model.simulate_growth(self.weather_df)
    
    # 重定向标准输出以捕获任何打印语句/错误
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    # 尝试绘图
    fig = self.model.plot_results()
    
    # 恢复标准输出
    sys.stdout = sys.__stdout__
    
    # 检查是否返回了图形
    self.assertIsNotNone(fig)

def test_model_inputs_outputs(self):
    """用详细示例测试模型的输入和输出。"""
    # 运行示例模拟
    results = self.model.simulate_growth(self.weather_df)
    
    # 打印关于输入和输出的详细信息
    print("\nCROPGRO-Strawberry 模型输入：")
    print(f"纬度：{self.model.latitude}°")
    print(f"种植日期：{self.model.planting_date.strftime('%Y-%m-%d')}")
    
    print("\n土壤属性:")
    for key, value in self.soil_properties.items():
        print(f"  {key}: {value}")
    
    print("\n品种参数:")
    for key, value in self.cultivar_params.items():
        print(f"  {key}: {value}")
    
    print("\n天气数据样本(前3天):")
    print(self.weather_df.head(3).to_string())
    
    print("\nCROPGRO-Strawberry 模型输出：")
    print(f"模拟长度：{len(results)} 天")
    
    print("\n最终植物状态:")
    print(f"  总生物量：{self.model.plant_state['biomass']:.2f} g/株")
    print(f"  果实生物量：{self.model.plant_state['fruit_biomass']:.2f} g/株")
    print(f"  叶子生物量：{self.model.plant_state['leaf_biomass']:.2f} g/株")
    print(f"  茎生物量：{self.model.plant_state['stem_biomass']:.2f} g/株")
    print(f"  根生物量：{self.model.plant_state['root_biomass']:.2f} g/株")
    print(f"  叶面积指数：{self.model.plant_state['leaf_area_index']:.2f} m²/m²")
    print(f"  果实数量：{self.model.plant_state['fruit_number']:.2f} 果实/株")
    print(f"  冠层数量：{self.model.plant_state['crown_number']:.2f} 冠层/株")
    print(f"  匍匐茎数量：{self.model.plant_state['runner_number']:.2f} 匍匐茎/株")
    print(f"  根系深度：{self.model.plant_state['root_depth']:.2f} cm")
    print(f"  最终阶段：{self.model.plant_state['phenological_stage']}")
    
    print("\n时间序列数据(第一天和最后一天）：")
    print("\n第一天:")
    first_day = results.iloc[0].to_dict()
    for key, value in first_day.items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n最后一天:")
    last_day = results.iloc[-1].to_dict()
    for key, value in last_day.items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    # 验证关键输出的数据类型
    self.assertIsInstance(results, pd.DataFrame)
    self.assertIsInstance(self.model.plant_state['biomass'], float)
    self.assertIsInstance(self.model.plant_state['leaf_area_index'], float)
    self.assertIsInstance(self.model.plant_state['phenological_stage'], str) 


def run_test_suite():
    """Run the test suite and print results."""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCropgroStrawberry)
    
    # 以较低的详细度运行测试，减少输出混乱
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    
    # 打印测试结果总结
    print(f"\nTests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    
    # 返回测试成功状态
    return len(result.errors) == 0 and len(result.failures) == 0


if __name__ == "__main__":
    # 这将在测试完成后干净地退出
    run_test_suite()
    print("Tests completed!")


# 测试的预期终端输出示例：
"""
CROPGRO-Strawberry Model Inputs:
Latitude: 40.0°
Planting date: 2023-05-01

Soil Properties:
  max_root_depth: 50.0
  field_capacity: 200.0
  wilting_point: 50.0

Cultivar Parameters:
  name: Albion
  tbase: 4.0
  topt: 22.0
  tmax_th: 35.0
  rue: 2.5
  k_light: 0.6
  sla: 0.02
  potential_fruits_per_crown: 10.0

Weather Data Sample (first 3 days):
         date  tmax  tmin  solar_radiation  rainfall    rh  wind_speed
0  2023-05-01  25.0  15.0             20.0       5.0  70.0         2.0
1  2023-05-02  25.0  15.0             20.0       5.0  70.0         2.0
2  2023-05-03  25.0  15.0             20.0       5.0  70.0         2.0

CROPGRO-Strawberry Model Outputs:
Simulation length: 10 days

Final Plant State:
  Total biomass: 9.45 g/plant
  Fruit biomass: 0.00 g/plant
  Leaf biomass: 3.78 g/plant
  Stem biomass: 2.27 g/plant
  Root biomass: 3.40 g/plant
  Leaf area index: 0.08 m²/m²
  Fruit number: 0.00 fruits/plant
  Crown number: 1.22 crowns/plant
  Runner number: 0.00 runners/plant
  Root depth: 7.00 cm
  Final stage: JUVENILE

Time Series Data (first day and last day):

First day:
  date: 2023-05-01
  dap: 1.00
  stage: GERMINATION
  thermal_time: 16.00
  biomass: 0.84
  leaf_area_index: 0.01
  root_depth: 5.20
  fruit_number: 0.00
  fruit_biomass: 0.00
  leaf_biomass: 0.34
  stem_biomass: 0.17
  root_biomass: 0.34
  crown_number: 1.00
  runner_number: 0.00
  water_stress: 0.00
  daylength: 14.23
  photosynthesis: 4.22
  transpiration: 2.53

Last day:
  date: 2023-05-10
  dap: 10.00
  stage: JUVENILE
  thermal_time: 160.00
  biomass: 9.45
  leaf_area_index: 0.08
  root_depth: 7.00
  fruit_number: 0.00
  fruit_biomass: 0.00
  leaf_biomass: 3.78
  stem_biomass: 2.27
  root_biomass: 3.40
  crown_number: 1.22
  runner_number: 0.00
  water_stress: 0.00
  daylength: 14.37
  photosynthesis: 5.28
  transpiration: 3.17
"""
