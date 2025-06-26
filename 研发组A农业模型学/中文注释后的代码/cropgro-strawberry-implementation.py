"""Python implementation of the CROPGRO-Strawberry crop growth model.

This module contains a simplified, purely Python implementation of the
CROPGRO strawberry model.  The structure mirrors the original Fortran
code but trades some complexity for readability.  All major calculation
steps are implemented as small functions decorated with ``@njit`` to keep
them fast when the optional ``numba`` dependency is available.
"""
# 模块文档字符串：介绍CROPGRO草莓模型的Python简化实现，说明其与Fortran原版的关系及性能优化方式

# CROPGRO-Strawberry Model Implementation in Python
# This is a simplified implementation of the CROPGRO model for strawberries

import numpy as np  # 导入NumPy库，用于数值计算
import pandas as pd  # 导入Pandas库，用于数据处理和分析
from datetime import datetime, timedelta  # 导入日期时间处理模块
import matplotlib.pyplot as plt  # 导入Matplotlib库，用于结果可视化

from dataclasses import dataclass, asdict  # 导入数据类相关功能，用于创建轻量级数据结构
from numba import njit  # 导入Numba的njit装饰器，用于编译优化函数

@dataclass  # 使用dataclass装饰器创建植物状态数据类
class PlantState:
    biomass: float = 0.0  # 植物总生物量(g/株)
    leaf_area_index: float = 0.1  # 叶面积指数(m²/m²)
    root_depth: float = 5.0  # 根系深度(cm)
    fruit_number: float = 0.0  # 果实数量(个/株)
    fruit_biomass: float = 0.0  # 果实生物量(g/株)
    leaf_biomass: float = 0.0  # 叶片生物量(g/株)
    stem_biomass: float = 0.0  # 茎生物量(g/株)
    root_biomass: float = 0.0  # 根系生物量(g/株)
    phenological_stage: str = "GERMINATION"  # 物候期
    development_rate: float = 0.0  # 发育速率
    crown_number: float = 1.0  # 冠数(个/株)
    runner_number: float = 0.0  # 匍匐茎数(个/株)

@njit  # 使用numba的njit装饰器加速函数执行
def _calc_daylength(latitude, day_of_year):
    """Return length of the day in hours for a given latitude and date."""
    # 计算给定纬度和日期的日长(小时)
    declination = 23.45 * np.sin(np.deg2rad(360 * (day_of_year - 80) / 365))  # 计算太阳赤纬角
    lat_rad = np.deg2rad(latitude)  # 将纬度转换为弧度
    term = -np.tan(lat_rad) * np.tan(np.deg2rad(declination))  # 日长方程中间项
    if term >= 1.0:
        return 0.0  # 极夜情况
    elif term <= -1.0:
        return 24.0  # 极昼情况
    else:
        return 24.0 * np.arccos(term) / np.pi  # 计算实际日长

@njit
def _thermal_time(tmin, tmax, tbase, topt, tmax_th):
    """Calculate thermal time accumulation for a single day."""
    # 计算单日积温(度日)
    tavg = (tmin + tmax) / 2.0  # 日平均温度
    if tavg <= tbase:
        return 0.0  # 低于基点温度，无积温
    elif tavg <= topt:
        return tavg - tbase  # 在基点和最适温度之间，线性积温
    elif tavg <= tmax_th:
        # 在最适和最高温度之间，非线性积温计算
        return (topt - tbase - (tavg - topt) * 
                ((topt - tbase) / (tmax_th - topt)))
    else:
        return 0.0  # 高于最高温度，无积温

@njit
def _photosynthesis(solar_radiation, tmax, tmin, rue, tbase, topt, 
                    k_light, lai, co2):
    """Estimate daily photosynthesis based on temperature and light."""
    # 基于温度和光照估算每日光合作用
    tavg = (tmax + tmin) / 2.0  # 日平均温度
    if tavg <= tbase:
        temp_effect = 0.0  # 温度影响因子
    elif tavg >= topt:
        temp_effect = 1.0
    else:
        temp_effect = (tavg - tbase) / (topt - tbase)  # 温度对光合作用的影响
    co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)  # CO2浓度对光合作用的影响
    light_interception = 1.0 - np.exp(-k_light * lai)  # 冠层光截获率
    # 计算光合作用速率
    return (solar_radiation * rue * temp_effect * co2_effect * 
            light_interception)

@njit
def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    """Compute potential plant transpiration using a simple ET0 approach."""
    # 使用简化的ET0方法计算潜在植物蒸腾量
    tavg = (tmax + tmin) / 2.0  # 日平均温度
    # 简化的参考作物蒸散量(Hargreaves方法)
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)
    # 基于冠层发育的作物系数
    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    return et0 * kc  # 计算作物蒸腾量

@njit
def _water_stress(field_capacity, wilting_point, root_depth, rainfall, 
                  transpiration):
    """Derive a water stress factor from soil moisture balance."""
    # 基于土壤水分平衡推导水分胁迫因子
    available_water = (field_capacity - wilting_point) * root_depth  # 根区有效水分
    effective_rainfall = rainfall * 0.7  # 有效降雨量(假设70%被土壤吸收)
    deficit = max(0.0, transpiration - effective_rainfall)  # 水分亏缺
    if deficit == 0.0:
        return 0.0  # 无水分胁迫
    else:
        stress_factor = min(1.0, deficit / available_water)  # 计算水分胁迫因子
        return stress_factor

@njit
def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass, 
                      fruit_biomass, tmin, tmax):
    """Calculate maintenance respiration of all plant organs."""
    # 计算植物各器官的维持呼吸
    tavg = (tmin + tmax) / 2.0  # 日平均温度
    temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)  # 温度响应因子(Q10模型)
    # 各器官特定呼吸速率
    resp_leaf = leaf_biomass * 0.03 * temp_factor  # 叶片呼吸
    resp_stem = stem_biomass * 0.015 * temp_factor  # 茎呼吸
    resp_root = root_biomass * 0.01 * temp_factor  # 根呼吸
    resp_fruit = fruit_biomass * 0.01 * temp_factor  # 果实呼吸
    return resp_leaf + resp_stem + resp_root + resp_fruit  # 总维持呼吸

class CropgroStrawberry:
    """
    A Python implementation of the CROPGRO-Strawberry crop model.
    
    This model simulates strawberry growth and development based on 
    environmental conditions, plant characteristics, and management practices.
    """
    
    def __init__(self, latitude, planting_date, soil_properties, 
                 cultivar_params):
        """
        Initialize the CROPGRO-Strawberry model.
        
        Parameters:
        -----------
        latitude : float
            Site latitude in decimal degrees
        planting_date : str
            Planting date in format 'YYYY-MM-DD'
        soil_properties : dict
            Dictionary containing soil properties
        cultivar_params : dict
            Dictionary containing cultivar-specific parameters
        """
        self.latitude = latitude  # 站点纬度
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')  # 种植日期
        self.soil = soil_properties  # 土壤属性
        self.cultivar = cultivar_params  # 品种参数
        
        self.days_after_planting = 0  # 种植后天数
        self.plant_state = PlantState()  # 初始化植物状态
        
        self.thermal_time = 0.0  # 累积积温(度日)
        
        # 物候期及其所需积温
        self.phenology_stages = {
            'GERMINATION': 0,         # 发芽期
            'EMERGENCE': 50,          # 出苗期
            'JUVENILE': 100,          # 幼年期
            'VEGETATIVE': 200,        # 营养生长期
            'FLORAL_INDUCTION': 400,  # 花芽分化期
            'FLOWERING': 600,         # 开花期
            'FRUIT_SET': 700,         # 坐果期
            'FRUIT_DEVELOPMENT': 800, # 果实发育期
            'FRUIT_MATURITY': 1000,   # 果实成熟期
            'SENESCENCE': 1500        # 衰老期
        }
        
        self.results = []  # 存储模拟结果
    
    def calculate_daylength(self, day_of_year):
        """计算基于纬度和一年中天数的日长"""
        return _calc_daylength(self.latitude, day_of_year)  # 调用日长计算函数
    
    def calculate_thermal_time(self, tmin, tmax):
        """计算基于日温度的积温"""
        tbase = self.cultivar['tbase']  # 基点温度
        topt = self.cultivar['topt']    # 最适温度
        tmax_th = self.cultivar['tmax_th']  # 最高温度阈值
        return _thermal_time(tmin, tmax, tbase, topt, tmax_th)  # 调用积温计算函数
    
    def update_phenology(self, thermal_time_today):
        """基于累积积温更新植物物候期"""
        self.thermal_time += thermal_time_today  # 累加今日积温
        current_stage = self.plant_state.phenological_stage  # 当前物候期
        stages = list(self.phenology_stages.keys())  # 物候期列表
        current_index = stages.index(current_stage)  # 当前物候期索引
        
        # 如果不是最后一个物候期且积温超过下一物候期阈值，则更新物候期
        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            if self.thermal_time >= self.phenology_stages[next_stage]:
                self.plant_state.phenological_stage = next_stage
    
    def calculate_photosynthesis(self, solar_radiation, tmax, tmin, co2=400):
        """计算每日光合作用速率"""
        rue = self.cultivar['rue']  # 辐射利用效率
        lai = self.plant_state.leaf_area_index  # 叶面积指数
        # 调用光合作用计算函数
        return _photosynthesis(
            solar_radiation,
            tmax,
            tmin,
            rue,
            self.cultivar['tbase'],
            self.cultivar['topt'],
            self.cultivar['k_light'],
            lai,
            co2,
        )
    
    def calculate_transpiration(self, solar_radiation, tmax, tmin, rh, wind_speed):
        """使用简化的Penman-Monteith方法计算植物蒸腾"""
        lai = self.plant_state.leaf_area_index  # 叶面积指数
        base_transpiration = _transpiration(solar_radiation, tmax, tmin, rh, lai)  # 基础蒸腾量
        
        # 风速对蒸腾的影响修正
        wind_modifier = 1.0 + 0.1 * (wind_speed - 2.0)  # 基于2m/s的基准风速
        wind_modifier = max(0.5, min(2.0, wind_modifier))  # 限制修正因子范围
        
        return base_transpiration * wind_modifier  # 返回修正后的蒸腾量
    
    def partition_biomass(self, daily_biomass):
        """基于发育阶段将新生物量分配到植物器官"""
        stage = self.plant_state.phenological_stage  # 当前物候期
        
        # 根据物候期确定分配比例
        if stage in ['GERMINATION', 'EMERGENCE', 'JUVENILE']:
            root_fraction, leaf_fraction, stem_fraction, fruit_fraction = 0.4, 0.4, 0.2, 0.0
        elif stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            root_fraction, leaf_fraction, stem_fraction, fruit_fraction = 0.2, 0.5, 0.3, 0.0
        elif stage == 'FLOWERING':
            root_fraction, leaf_fraction, stem_fraction, fruit_fraction = 0.1, 0.4, 0.3, 0.2
        elif stage in ['FRUIT_SET', 'FRUIT_DEVELOPMENT']:
            root_fraction, leaf_fraction, stem_fraction, fruit_fraction = 0.05, 0.25, 0.2, 0.5
        elif stage == 'FRUIT_MATURITY':
            root_fraction, leaf_fraction, stem_fraction, fruit_fraction = 0.0, 0.1, 0.1, 0.8
        else:  # 'SENESCENCE'
            root_fraction, leaf_fraction, stem_fraction, fruit_fraction = 0.0, 0.0, 0.0, 0.0
        
        # 向各器官添加新生物量
        self.plant_state.root_biomass += daily_biomass * root_fraction
        self.plant_state.leaf_biomass += daily_biomass * leaf_fraction
        self.plant_state.stem_biomass += daily_biomass * stem_fraction
        self.plant_state.fruit_biomass += daily_biomass * fruit_fraction
        
        # 更新总生物量
        self.plant_state.biomass = (
            self.plant_state.root_biomass
            + self.plant_state.leaf_biomass
            + self.plant_state.stem_biomass
            + self.plant_state.fruit_biomass
        )
        
        # 基于新叶生物量更新叶面积指数
        sla = self.cultivar['sla']  # 比叶面积
        if stage in ['FRUIT_DEVELOPMENT', 'FRUIT_MATURITY', 'SENESCENCE']:
            sla *= 0.8  # 后期阶段比叶面积降低
            
        self.plant_state.leaf_area_index = self.plant_state.leaf_biomass * sla
        
        # 更新根系深度
        max_root_growth_rate = 0.5  # 最大根系生长速率(cm/天)
        max_root_depth = self.soil['max_root_depth']  # 最大根系深度
        
        potential_root_growth = max_root_growth_rate * root_fraction  # 潜在根系生长量
        current_root_depth = self.plant_state.root_depth
        
        # 如果当前根系深度小于最大深度，则更新根系深度
        if current_root_depth < max_root_depth:
            self.plant_state.root_depth = min(
                current_root_depth + potential_root_growth, max_root_depth)
    
    def update_runners(self):
        """基于发育阶段和条件更新匍匐茎数量"""
        # 匍匐茎主要在旺盛营养生长期产生
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            self.plant_state.runner_number += 0.1 * self.plant_state.crown_number  # 增加匍匐茎数量
    
    def update_crowns(self):
        """基于发育阶段和条件更新冠数"""
        # 草莓植株在活跃生长期可分支形成多个冠
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION', 'FLOWERING']:
            self.plant_state.crown_number += 0.02 * self.plant_state.crown_number  # 增加冠数
    
    def update_fruits(self):
        """更新果实数量和单果重量"""
        stage = self.plant_state.phenological_stage  # 当前物候期
        
        # 在开花期和坐果期形成新果实
        if stage == 'FLOWERING':
            new_fruits = (self.cultivar['potential_fruits_per_crown'] * 
                          self.plant_state.crown_number * 0.1)
            self.plant_state.fruit_number += new_fruits
        elif stage == 'FRUIT_SET':
            new_fruits = (self.cultivar['potential_fruits_per_crown'] * 
                          self.plant_state.crown_number * 0.2)
            self.plant_state.fruit_number += new_fruits
    
    def simulate_day(self, weather_data):
        """模拟草莓一天的生长"""
        self.days_after_planting += 1  # 增加种植后天数计数器
        
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')  # 当前日期
        day_of_year = current_date.timetuple().tm_yday  # 一年中的天数
        
        daylength = self.calculate_daylength(day_of_year)  # 计算日长
        
        thermal_time_today = self.calculate_thermal_time(  # 计算今日积温
            weather_data['tmin'], weather_data['tmax'])
        
        self.update_phenology(thermal_time_today)  # 更新物候期
        
        # 计算每日光合产量
        photosynthesis = self.calculate_photosynthesis(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin']
        )
        
        # 计算潜在蒸腾量
        transpiration = self.calculate_transpiration(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin'],
            weather_data['rh'],
            weather_data['wind_speed']
        )
        
        # 计算水分胁迫
        water_stress = self.calculate_water_stress(
            weather_data['rainfall'], transpiration)
        
        photosynthesis *= (1 - water_stress)  # 考虑水分胁迫对光合作用的影响
        
        # 将冠层同化量转换为单株生物量(假设5株/m²)
        plant_density = 5.0  # 植株密度(株/m²)
        daily_biomass = photosynthesis / plant_density  # 每日生物量增量
        
        # 从产生的生物量中减去呼吸消耗
        maintenance_resp = self.calculate_maintenance_respiration(
            weather_data['tmin'], weather_data['tmax'])
        daily_biomass = max(0, daily_biomass - maintenance_resp)  # 净生物量增量
        
        self.partition_biomass(daily_biomass)  # 分配生物量到各器官
        
        # 更新匍匐茎、冠和果实数量
        self.update_runners()
        self.update_crowns()
        self.update_fruits()
        
        # 存储当日结果
        self.results.append({
            'date': weather_data['date'],
            'dap': self.days_after_planting,
            'stage': self.plant_state.phenological_stage,
            'thermal_time': self.thermal_time,
            'biomass': self.plant_state.biomass,
            'leaf_area_index': self.plant_state.leaf_area_index,
            'root_depth': self.plant_state.root_depth,
            'fruit_number': self.plant_state.fruit_number,
            'fruit_biomass': self.plant_state.fruit_biomass,
            'leaf_biomass': self.plant_state.leaf_biomass,
            'stem_biomass': self.plant_state.stem_biomass,
            'root_biomass': self.plant_state.root_biomass,
            'crown_number': self.plant_state.crown_number,
            'runner_number': self.plant_state.runner_number,
            'water_stress': water_stress,
            'daylength': daylength,
            'photosynthesis': photosynthesis,
            'transpiration': transpiration
        })
    
    def calculate_water_stress(self, rainfall, transpiration):
        """计算基于土壤水分平衡的水分胁迫因子(0-1)"""
        field_capacity = self.soil['field_capacity']  # 田间持水量
        wilting_point = self.soil['wilting_point']  # 萎蔫点
        root_depth = self.plant_state.root_depth / 100.0  # 根系深度(m)
        return _water_stress(field_capacity, wilting_point, root_depth, 
                           rainfall, transpiration)  # 调用水分胁迫计算函数
    
    def calculate_maintenance_respiration(self, tmin, tmax):
        """基于生物量和温度计算维持呼吸"""
        return _maintenance_resp(
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            self.plant_state.fruit_biomass,
            tmin,
            tmax,
        )  # 调用维持呼吸计算函数
    
    def simulate_growth(self, weather_data_df):
        """模拟草莓在天气数据定义的时间段内的生长"""
        self.results = []  # 重置结果
        
        # 使用itertuples提高模拟速度
        for row in weather_data_df.itertuples(index=False):
            weather_day = {
                'date': row.date,
                'tmax': row.tmax,
                'tmin': row.tmin,
                'solar_radiation': row.solar_radiation,
                'rainfall': row.rainfall,
                'rh': row.rh,
                'wind_speed': row.wind_speed,
            }
            self.simulate_day(weather_day)  # 模拟每一天
        
        # 将结果转换为DataFrame
        self.results_df = pd.DataFrame(self.results)
        return self.results_df  # 返回结果DataFrame
    
    def plot_results(self):
        """绘制关键模拟结果"""
        if not hasattr(self, 'results_df') or len(self.results_df) == 0:
            print("No simulation results to plot. "
                  "Run simulate_growth() first.")
            return
        
        fig, axs = plt.subplots(3, 2, figsize=(14, 12))  # 创建子图
        
        # 绘制生物量
        axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 'b-', label='Total')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['leaf_biomass'], 'g-', label='Leaf')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['stem_biomass'], 'k-', label='Stem')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['root_biomass'], 'r-', label='Root')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['fruit_biomass'], 'm-', label='Fruit')
        axs[0, 0].set_xlabel('Days After Planting')
        axs[0, 0].set_ylabel('Biomass (g/plant)')
        axs[0, 0].set_title('Plant Biomass')
        axs[0, 0].legend()
        
        # 绘制叶面积指数
        axs[0, 1].plot(self.results_df['dap'], self.results_df['leaf_area_index'], 'g-')
        axs[0, 1].set_xlabel('Days After Planting')
        axs[0, 1].set_ylabel('LAI (m²/m²)')
        axs[0, 1].set_title('Leaf Area Index')
        
        # 绘制果实数量
        axs[1, 0].plot(self.results_df['dap'], self.results_df['fruit_number'], 'm-')
        axs[1, 0].set_xlabel('Days After Planting')
        axs[1, 0].set_ylabel('Fruits (number/plant)')
        axs[1, 0].set_title('Fruit Number')
        
        # 绘制冠和匍匐茎
        axs[1, 1].plot(self.results_df['dap'], self.results_df['crown_number'], 'b-', label='Crowns')
        axs[1, 1].plot(self.results_df['dap'], self.results_df['runner_number'], 'r-', label='Runners')
        axs[1, 1].set_xlabel('Days After Planting')
        axs[1, 1].set_ylabel('Number per plant')
        axs[1, 1].set_title('Crowns and Runners')
        axs[1, 1].legend()
        
        # 绘制水分胁迫
        axs[2, 0].plot(self.results_df['dap'], self.results_df['water_stress'], 'r-')
        axs[2, 0].set_xlabel('Days After Planting')
        axs[2, 0].set_ylabel('Water Stress (0-1)')
        axs[2, 0].set_title('Water Stress Factor')
        
        # 绘制物候期发育
        stages = list(self.phenology_stages.keys())
        stage_values = [stages.index(stage) for stage in self.results_df['stage']]
        axs[2, 1].plot(self.results_df['dap'], stage_values, 'b-')
        axs[2, 1].set_xlabel('Days After Planting')
        axs[2, 1].set_ylabel('Development Stage')
        axs[2, 1].set_yticks(range(len(stages)))
        axs[2, 1].set_yticklabels(stages)
        axs[2, 1].set_title('Phenological Development')
        
        plt.tight_layout()  # 调整子图布局
        return fig  # 返回图形对象


# Example usage of the CROPGRO-Strawberry model
def run_example_simulation():
    """运行模型与合成天气数据并返回结果"""
    # 定义土壤属性
    soil_properties = {
        'max_root_depth': 50.0,  # 最大根系深度(cm)
        'field_capacity': 200.0,  # 田间持水量(mm/m)
        'wilting_point': 50.0,   # 萎蔫点(mm/m)
    }
    
    # 定义品种参数
    cultivar_params = {
        'name': 'Albion',
        'tbase': 4.0,       # 基点温度(°C)
        'topt': 22.0,       # 最适温度(°C)
        'tmax_th': 35.0,    # 最高温度阈值(°C)
        'rue': 2.5,         # 辐射利用效率(g/MJ)
        'k_light': 0.6,     # 光衰减系数
        'sla': 0.02,        # 比叶面积(m²/g)
        'potential_fruits_per_crown': 10.0  # 每冠最大果实数
    }
    
    # 创建样本天气数据集
    start_date = '2023-05-01'
    end_date = '2023-10-31'
    
    dates = pd.date_range(start=start_date, end=end_date)  # 生成日期范围
    n_days = len(dates)  # 天数
    
    # 创建合成天气数据
    np.random.seed(42)  # 设置随机种子以确保可重复性
    
    # 温度遵循季节模式
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    seasonal_component = 10 * np.sin(2 * np.pi * (day_of_year - 172) / 365)
    
    tmax = 25.0 + seasonal_component + np.random.normal(0, 3, n_days)  # 最高温度
    tmin = 10.0 + seasonal_component + np.random.normal(0, 2, n_days)  # 最低温度
    
    # 太阳辐射遵循季节模式
    solar_rad = (15.0 + 10.0 * np.sin(2 * np.pi * (day_of_year - 172) / 365) 
                + np.random.normal(0, 2, n_days))
    solar_rad = np.maximum(1.0, solar_rad)  # 确保正辐射
    
    # 降雨-随机事件
    rainfall = np.zeros(n_days)
    rain_events = np.random.rand(n_days) < 0.3  # 每天30%的降雨概率
    rainfall[rain_events] = np.random.exponential(5, np.sum(rain_events))  # 降雨强度
    
    # 相对湿度和风速
    rh = 70.0 + np.random.normal(0, 10, n_days)  # 相对湿度
    rh = np.clip(rh, 20, 100)  # 限制在有效范围内
    
    wind_speed = 2.0 + np.random.exponential(1, n_days)  # 风速
    
    # 创建天气DataFrame
    weather_df = pd.DataFrame({
        'date': [d.strftime('%Y-%m-%d') for d in dates],
        'tmax': tmax,
        'tmin': tmin,
        'solar_radiation': solar_rad,
        'rainfall': rainfall,
        'rh': rh,
        'wind_speed': wind_speed
    })
    
    # 初始化模型
    model = CropgroStrawberry(
        latitude=40.0,  # 纬度
        planting_date=start_date,  # 种植日期
        soil_properties=soil_properties,  # 土壤属性
        cultivar_params=cultivar_params  # 品种参数
    )
    
    # 运行模拟
    results = model.simulate_growth(weather_df)  # 模拟生长
    
    # 绘制结果
    fig = model.plot_results()  # 绘制结果图
    
    return model, results, fig  # 返回模型、结果和图形对象


if __name__ == "__main__":
    # 运行示例模拟
    model, results, fig = run_example_simulation()
    
    # 显示一些结果
    print(f"Final biomass: {results['biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final fruit biomass: {results['fruit_biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final leaf area index: {results['leaf_area_index'].iloc[-1]:.2f} m²/m²")
    print(f"Final phenological stage: {results['stage'].iloc[-1]}")
    
    # 显示图
    plt.show()