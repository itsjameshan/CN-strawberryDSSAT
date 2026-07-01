# -*- coding: utf-8 -*-
"""
CROPGRO-Strawberry 草莓作物生长模型 - 核心源码（中文注释版）
=============================================================

本模块是草莓作物生长模型的核心实现，包含以下主要功能模块：

1. **PlantState (植物状态类)**
   - 存储植物各器官的生物量
   - 记录物候发育阶段
   - 追踪叶面积指数、果实数量等

2. **日照长度计算 (_calc_daylength)**
   - 根据纬度和日期计算日照长度
   - 用于光周期效应计算

3. **积温计算 (_thermal_time)**
   - 计算每日有效积温（度·日）
   - 考虑基温、最适温、最高临界温

4. **光合作用计算 (_photosynthesis)**
   - 根据光照、温度计算光合产量
   - 考虑CO2浓度和叶面积指数影响

5. **蒸腾计算 (_transpiration)**
   - 计算植物蒸腾量
   - 使用简化的Penman-Monteith方法

6. **水分胁迫计算 (_water_stress)**
   - 根据土壤水分平衡计算水分胁迫因子
   - 影响光合作用效率

7. **呼吸消耗计算 (_maintenance_resp)**
   - 计算维持呼吸消耗
   - 使用Q10温度模型

8. **CropgroStrawberry (模型主类)**
   - 整合所有计算模块
   - 模拟植物每日生长发育
   - 管理物候期转换
   - 生物量在各器官间的分配

作者：代码验证组
日期：2026-06-30
版本：1.0（中文注释版）
"""

# ============================================================================
# 导入必要的库
# ============================================================================
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dataclasses import dataclass, asdict
from numba import njit


# ============================================================================
# 数据类：定义植物状态数据结构
# ============================================================================
@dataclass
class PlantState:
    """
    植物状态数据类
    -----------------
    存储植物生长过程中的关键状态变量，包括各器官生物量、物候阶段等。
    
    属性说明：
    - biomass: 植物总生物量 (g/plant)
    - leaf_area_index: 叶面积指数 (m²/m²)
    - root_depth: 根系深度 (cm)
    - fruit_number: 果实数量 (个/株)
    - fruit_biomass: 果实生物量 (g/plant)
    - leaf_biomass: 叶片生物量 (g/plant)
    - stem_biomass: 茎干生物量 (g/plant)
    - root_biomass: 根系生物量 (g/plant)
    - phenological_stage: 当前物候阶段
    - development_rate: 发育速率
    - crown_number: 冠数量
    - runner_number: 匍匐茎数量
    """
    biomass: float = 0.0          # 植物总生物量 (g/plant)
    leaf_area_index: float = 0.1   # 叶面积指数 (m²/m²)
    root_depth: float = 5.0        # 根系深度 (cm)
    fruit_number: float = 0.0      # 果实数量 (个/株)
    fruit_biomass: float = 0.0     # 果实生物量 (g/plant)
    leaf_biomass: float = 0.0     # 叶片生物量 (g/plant)
    stem_biomass: float = 0.0     # 茎干生物量 (g/plant)
    root_biomass: float = 0.0     # 根系生物量 (g/plant)
    phenological_stage: str = "GERMINATION"  # 物候阶段
    development_rate: float = 0.0 # 发育速率
    crown_number: float = 1.0     # 冠数量
    runner_number: float = 0.0     # 匍匐茎数量


# ============================================================================
# 计算函数：日照长度
# ============================================================================
@njit
def _calc_daylength(latitude, day_of_year):
    """
    计算日照长度
    ------------
    根据给定纬度和一年中的日期计算当日的日照时数。
    
    算法基于天文日照计算公式，考虑了地球自转轴倾角。
    
    参数：
        latitude (float): 纬度（度），正值表示北纬，负值表示南纬
        day_of_year (int): 一年中的第几天 (1-366)
    
    返回：
        float: 日照长度（小时），范围0-24小时
    
    算法说明：
        1. 计算太阳赤纬角（solar declination）
        2. 将纬度转换为弧度
        3. 计算日照长度公式中的中间项
        4. 根据中间项的值判断极昼/极夜情况
    """
    # 计算太阳赤纬角 - 描述地球自转轴倾斜的角度
    # 使用简化公式：declination = 23.45 * sin(360*(DOY-80)/365)
    declination = 23.45 * np.sin(np.deg2rad(360 * (day_of_year - 80) / 365))
    
    # 将纬度转换为弧度（三角函数需要弧度制）
    lat_rad = np.deg2rad(latitude)
    
    # 计算日照长度公式的中间项
    # 这是一个经典的日照长度计算公式
    term = -np.tan(lat_rad) * np.tan(np.deg2rad(declination))
    
    # 判断极昼/极夜情况
    if term >= 1.0:
        # 北极圈内的极夜现象（24小时黑暗）
        return 0.0
    elif term <= -1.0:
        # 北极圈内的极昼现象（24小时白昼）
        return 24.0
    else:
        # 正常情况：计算日照长度
        return 24.0 * np.arccos(term) / np.pi


# ============================================================================
# 计算函数：积温
# ============================================================================
@njit
def _thermal_time(tmin, tmax, tbase, topt, tmax_th):
    """
    计算每日积温（有效温度）
    ------------------------
    根据日最高温和最低温计算当日的有效积温（度·日，DD）。
    
    积温是作物生长发育的重要指标，表示作物实际获得的热量。
    
    参数：
        tmin (float): 日最低温度 (°C)
        tmax (float): 日最高温度 (°C)
        tbase (float): 发育基温，低于此温度作物不发育 (°C)
        topt (float): 发育最适温度，在此温度下发育最快 (°C)
        tmax_th (float): 发育最高临界温度，超过此温度发育停止 (°C)
    
    返回：
        float: 当日有效积温 (°C·day)
    
    算法说明：
        1. 计算平均温度 Tavg = (Tmax + Tmin) / 2
        2. 分三种情况计算有效积温：
           - Tavg <= Tbase: 返回0（温度太低，无效）
           - Tbase < Tavg <= Topt: 返回 Tavg - Tbase
           - Topt < Tavg <= Tmax_th: 使用线性插值计算（高温抑制）
           - Tavg > Tmax_th: 返回0（温度太高，有抑制）
    """
    # 计算平均日温度
    tavg = (tmin + tmax) / 2.0
    
    # 情况1：温度低于基温，无效积温
    if tavg <= tbase:
        return 0.0
    # 情况2：温度在最适范围，正常计算积温
    elif tavg <= topt:
        return tavg - tbase
    # 情况3：温度高于最适但低于临界，使用线性递减
    elif tavg <= tmax_th:
        # 温度过高时，有效积温开始递减
        return (topt - tbase - (tavg - topt) * 
                ((topt - tbase) / (tmax_th - topt)))
    # 情况4：温度超过临界值，无效
    else:
        return 0.0


# ============================================================================
# 计算函数：光合作用
# ============================================================================
@njit
def _photosynthesis(solar_radiation, tmax, tmin, rue, tbase, topt, 
                    k_light, lai, co2):
    """
    计算每日光合作用速率
    --------------------
    根据当日的辐射、温度、CO2浓度和叶面积指数计算光合产量。
    
    参数：
        solar_radiation (float): 日太阳辐射 (MJ/m²)
        tmax (float): 日最高温度 (°C)
        tmin (float): 日最低温度 (°C)
        rue (float): 辐射利用效率 (g MJ⁻¹)
        tbase (float): 发育基温 (°C)
        topt (float): 发育最适温度 (°C)
        k_light (float): 光消光系数
        lai (float): 叶面积指数 (m²/m²)
        co2 (float): 大气CO2浓度 (ppm)
    
    返回：
        float: 每日光合产量 (g CH2O/m²/day)
    
    算法说明：
        1. 温度效应：计算温度对光合速率的影响
        2. CO2效应：CO2浓度增加会提高光合效率
        3. 冠层截获光：1 - exp(-k*LAI) 表示冠层截获光的比例
        4. 最终光合产量 = 辐射 × 辐射利用效率 × 各效应因子
    """
    # 计算平均温度用于温度效应计算
    tavg = (tmax + tmin) / 2.0
    
    # 温度效应计算
    if tavg <= tbase:
        # 温度太低，光合作用停止
        temp_effect = 0.0
    elif tavg >= topt:
        # 温度在最适以上，效应为1（简化处理）
        temp_effect = 1.0
    else:
        # 在基温和最适温之间，线性插值
        temp_effect = (tavg - tbase) / (topt - tbase)
    
    # CO2浓度效应
    # CO2浓度增加会提高光合效率（光合酶活性增强）
    # 公式基于CO2饱和曲线的对数近似
    co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)
    
    # 冠层光截获比例
    # 使用Beer-Lambert定律：I = I0 * exp(-k*LAI)
    # 截获比例 = 1 - exp(-k*LAI)
    light_interception = 1.0 - np.exp(-k_light * lai)
    
    # 计算最终光合产量
    return (solar_radiation * rue * temp_effect * co2_effect * light_interception)


# ============================================================================
# 计算函数：蒸腾作用
# ============================================================================
@njit
def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    """
    计算潜在蒸腾量
    --------------
    使用简化的Hargreaves方法计算参考作物蒸腾量，然后根据叶面积进行调整。
    
    参数：
        solar_radiation (float): 日太阳辐射 (MJ/m²)
        tmax (float): 日最高温度 (°C)
        tmin (float): 日最低温度 (°C)
        rh (float): 相对湿度 (%)
        lai (float): 叶面积指数 (m²/m²)
    
    返回：
        float: 潜在蒸腾量 (mm/day)
    
    算法说明：
        1. 使用Hargreaves公式计算参考蒸腾量ET0
        2. 根据LAI计算作物系数Kc
        3. 最终蒸腾量 = ET0 × Kc
    """
    # 计算平均温度
    tavg = (tmax + tmin) / 2.0
    
    # Hargreaves参考蒸腾量公式
    # 这是一个仅需要温度和辐射的简化ET计算方法
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)
    
    # 作物系数 - 随LAI增加而增加
    # LAI=0时 Kc=0.3（仅有土壤蒸发）
    # LAI增大时 Kc增加，最大约1.0
    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    
    return et0 * kc


# ============================================================================
# 计算函数：水分胁迫
# ============================================================================
@njit
def _water_stress(field_capacity, wilting_point, root_depth, rainfall, 
                  transpiration):
    """
    计算水分胁迫因子
    ----------------
    根据土壤水分平衡计算作物受到的水分胁迫程度。
    
    参数：
        field_capacity (float): 田间持水量 (mm/m)
        wilting_point (float): 萎蔫点 (mm/m)
        root_depth (float): 根系深度 (m)
        rainfall (float): 日降雨量 (mm)
        transpiration (float): 日蒸腾量 (mm)
    
    返回：
        float: 水分胁迫因子 (0-1)，0表示无胁迫，1表示最大胁迫
    
    算法说明：
        1. 计算根系层有效土壤水量 = (田间持水量 - 萎蔫点) × 根系深度
        2. 计算有效降雨（假设70%降雨转化为有效水分）
        3. 计算水分亏缺 = max(0, 蒸腾量 - 有效降雨)
        4. 胁迫因子 = min(1, 亏缺量 / 有效土壤水量)
    """
    # 计算根系层总有效土壤水量 (mm)
    available_water = (field_capacity - wilting_point) * root_depth
    
    # 有效降雨量（假设30%地表径流或蒸发损失）
    effective_rainfall = rainfall * 0.7
    
    # 计算水分亏缺 = 蒸腾需求 - 有效供水
    deficit = max(0.0, transpiration - effective_rainfall)
    
    # 如果没有亏缺，则无胁迫
    if deficit == 0.0:
        return 0.0
    else:
        # 计算胁迫因子，限制在0-1之间
        stress_factor = min(1.0, deficit / available_water)
        return stress_factor


# ============================================================================
# 计算函数：维持呼吸
# ============================================================================
@njit
def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass, 
                      fruit_biomass, tmin, tmax):
    """
    计算维持呼吸消耗
    ----------------
    计算植物各器官用于维持生命的呼吸消耗。
    
    参数：
        leaf_biomass (float): 叶片生物量 (g)
        stem_biomass (float): 茎干生物量 (g)
        root_biomass (float): 根系生物量 (g)
        fruit_biomass (float): 果实生物量 (g)
        tmin (float): 日最低温度 (°C)
        tmax (float): 日最高温度 (°C)
    
    返回：
        float: 日维持呼吸消耗总量 (g CH2O/day)
    
    算法说明：
        1. 使用Q10温度模型：温度每升高10°C，呼吸速率增加1倍
        2. 各器官的基础呼吸速率不同：
           - 叶片：3% (最活跃，代谢旺盛)
           - 茎干：1.5%
           - 根系：1%
           - 果实：1%
    """
    # 计算平均温度
    tavg = (tmin + tmax) / 2.0
    
    # Q10温度效应因子
    # 基准温度20°C，每升高10°C，呼吸速率翻倍
    temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)
    
    # 各器官呼吸消耗 = 生物量 × 呼吸速率 × 温度因子
    resp_leaf = leaf_biomass * 0.03 * temp_factor   # 叶片呼吸率最高
    resp_stem = stem_biomass * 0.015 * temp_factor  # 茎干次之
    resp_root = root_biomass * 0.01 * temp_factor   # 根系较低
    resp_fruit = fruit_biomass * 0.01 * temp_factor # 果实最低
    
    return resp_leaf + resp_stem + resp_root + resp_fruit


# ============================================================================
# 主类：CROPGRO-Strawberry 草莓生长模型
# ============================================================================
class CropgroStrawberry:
    """
    CROPGRO-Strawberry 草莓生长模型主类
    =====================================
    
    本模型模拟草莓在给定环境条件下的生长发育过程，包括：
    - 物候发育阶段转换
    - 光合作用和呼吸消耗
    - 生物量积累和分配
    - 果实产量形成
    - 水分胁迫响应
    
    使用方法：
        1. 创建模型实例：提供地点、播期、土壤和品种参数
        2. 准备气象数据DataFrame
        3. 调用simulate_growth()运行模拟
        4. 获取结果并使用plot_results()可视化
    
    示例：
        >>> model = CropgroStrawberry(
        ...     latitude=40.0,
        ...     planting_date='2023-05-01',
        ...     soil_properties=soil_props,
        ...     cultivar_params=cultivar
        ... )
        >>> results = model.simulate_growth(weather_df)
        >>> fig = model.plot_results()
    """
    
    def __init__(self, latitude, planting_date, soil_properties, cultivar_params):
        """
        初始化CROPGRO-Strawberry模型
        
        参数：
            latitude (float): 地点纬度（度）
            planting_date (str): 播种日期，格式'YYYY-MM-DD'
            soil_properties (dict): 土壤参数字典，包含：
                - max_root_depth: 最大根系深度 (cm)
                - field_capacity: 田间持水量 (mm/m)
                - wilting_point: 萎蔫点 (mm/m)
            cultivar_params (dict): 品种参数字典，包含：
                - name: 品种名称
                - tbase: 发育基温 (°C)
                - topt: 发育最适温 (°C)
                - tmax_th: 发育最高临界温 (°C)
                - rue: 辐射利用效率 (g/MJ)
                - k_light: 光消光系数
                - sla: 比叶面积 (m²/g)
                - potential_fruits_per_crown: 每冠潜在果实数
        """
        # 保存模型参数
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        
        # 初始化状态变量
        self.days_after_planting = 0  # 播后天数
        self.plant_state = PlantState() # 植物状态
        
        # 累积积温（度·日）
        self.thermal_time = 0.0
        
        # 物候阶段及其积温阈值
        # 作物需要累积足够的积温才能从一个阶段进入下一个阶段
        self.phenology_stages = {
            'GERMINATION': 0,        # 发芽期：0度·日
            'EMERGENCE': 50,         # 出苗期：50度·日
            'JUVENILE': 100,         # 幼苗期：100度·日
            'VEGETATIVE': 200,       # 营养生长期：200度·日
            'FLORAL_INDUCTION': 400, # 花芽分化期：400度·日
            'FLOWERING': 600,        # 开花期：600度·日
            'FRUIT_SET': 700,        # 坐果期：700度·日
            'FRUIT_DEVELOPMENT': 800,# 果实发育期：800度·日
            'FRUIT_MATURITY': 1000,  # 成熟期：1000度·日
            'SENESCENCE': 1500       # 衰老期：1500度·日
        }
        
        # 结果存储列表
        self.results = []
    
    def simulate_day(self, weather_data):
        """
        模拟一天的草莓生长发育
        
        这是模型的核心方法，按顺序执行以下计算步骤：
        1. 更新播后天数
        2. 计算日照长度
        3. 计算当日积温
        4. 更新物候阶段
        5. 计算光合作用
        6. 计算蒸腾和水分胁迫
        7. 计算呼吸消耗
        8. 分配生物量到各器官
        9. 更新匍匐茎和冠数
        10. 更新果实数量
        11. 保存当日结果
        
        参数：
            weather_data (dict): 当日气象数据，包含：
                - date: 日期 (YYYY-MM-DD)
                - tmax: 最高温度 (°C)
                - tmin: 最低温度 (°C)
                - solar_radiation: 太阳辐射 (MJ/m²)
                - rainfall: 降雨量 (mm)
                - rh: 相对湿度 (%)
                - wind_speed: 风速 (m/s)
        """
        # 1. 更新播后天数
        self.days_after_planting += 1
        
        # 2. 获取当前日期和年内日期
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
        day_of_year = current_date.timetuple().tm_yday
        
        # 3. 计算日照长度
        daylength = self.calculate_daylength(day_of_year)
        
        # 4. 计算当日积温
        thermal_time_today = self.calculate_thermal_time(
            weather_data['tmin'], weather_data['tmax'])
        
        # 5. 更新物候阶段（根据累积积温）
        self.update_phenology(thermal_time_today)
        
        # 6. 计算光合作用
        photosynthesis = self.calculate_photosynthesis(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin']
        )
        
        # 7. 计算蒸腾
        transpiration = self.calculate_transpiration(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin'],
            weather_data['rh'],
            weather_data['wind_speed']
        )
        
        # 8. 计算水分胁迫
        water_stress = self.calculate_water_stress(
            weather_data['rainfall'], transpiration)
        
        # 9. 水分胁迫降低光合效率
        photosynthesis *= (1 - water_stress)
        
        # 10. 转换单位：冠层光合产量 -> 单株生物量
        plant_density = 5.0  # 种植密度 (株/m²)
        daily_biomass = photosynthesis / plant_density
        
        # 11. 扣除呼吸消耗
        maintenance_resp = self.calculate_maintenance_respiration(
            weather_data['tmin'], weather_data['tmax'])
        daily_biomass = max(0, daily_biomass - maintenance_resp)
        
        # 12. 生物量分配到各器官
        self.partition_biomass(daily_biomass)
        
        # 13. 更新匍匐茎和冠数
        self.update_runners()
        self.update_crowns()
        
        # 14. 更新果实数量
        self.update_fruits()
        
        # 15. 保存当日结果
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
    
    def partition_biomass(self, daily_biomass):
        """
        生物量分配
        -----------
        根据当前物候阶段，将每日净光合产物分配到各器官。
        
        分配原则：
        - 生长早期：优先分配给根和叶（建立营养结构）
        - 营养生长期：主要分配给叶片（扩大光合面积）
        - 开花结果期：逐渐转向果实（产量形成）
        - 成熟期：大量分配给果实（灌浆成熟）
        - 衰老期：停止生长，所有器官分配为0
        
        参数：
            daily_biomass (float): 当日净生物量产量 (g/plant)
        """
        stage = self.plant_state.phenological_stage
        
        # 根据物候阶段确定分配比例
        if stage in ['GERMINATION', 'EMERGENCE', 'JUVENILE']:
            # 幼苗期：重点建立根系和叶片
            root_fraction = 0.4   # 40%给根系
            leaf_fraction = 0.4  # 40%给叶片
            stem_fraction = 0.2  # 20%给茎干
            fruit_fraction = 0.0 # 暂无果实
        elif stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            # 营养生长期：继续扩大叶面积
            root_fraction = 0.2
            leaf_fraction = 0.5
            stem_fraction = 0.3
            fruit_fraction = 0.0
        elif stage == 'FLOWERING':
            # 开花期：开始向果实分配
            root_fraction = 0.1
            leaf_fraction = 0.4
            stem_fraction = 0.3
            fruit_fraction = 0.2
        elif stage in ['FRUIT_SET', 'FRUIT_DEVELOPMENT']:
            # 结果期：大量给果实
            root_fraction = 0.05
            leaf_fraction = 0.25
            stem_fraction = 0.2
            fruit_fraction = 0.5
        elif stage == 'FRUIT_MATURITY':
            # 成熟期：主要给果实灌浆
            root_fraction = 0.0
            leaf_fraction = 0.1
            stem_fraction = 0.1
            fruit_fraction = 0.8
        else:  # 'SENESCENCE'
            # 衰老期：停止生长
            root_fraction = 0.0
            leaf_fraction = 0.0
            stem_fraction = 0.0
            fruit_fraction = 0.0
        
        # 分配生物量到各器官
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
        
        # 更新叶面积指数
        sla = self.cultivar['sla']
        if stage in ['FRUIT_DEVELOPMENT', 'FRUIT_MATURITY', 'SENESCENCE']:
            sla *= 0.8  # 后期比叶面积降低（叶片变厚）
        self.plant_state.leaf_area_index = self.plant_state.leaf_biomass * sla
        
        # 更新根系深度
        max_root_growth_rate = 0.5  # 最大根系日伸长量 (cm/day)
        max_root_depth = self.soil['max_root_depth']
        potential_root_growth = max_root_growth_rate * root_fraction
        current_root_depth = self.plant_state.root_depth
        if current_root_depth < max_root_depth:
            self.plant_state.root_depth = min(
                current_root_depth + potential_root_growth, max_root_depth)
    
    def update_phenology(self, thermal_time_today):
        """
        更新物候阶段
        -------------
        根据累积积温判断是否进入下一个物候阶段。
        
        参数：
            thermal_time_today (float): 当日有效积温
        """
        # 累加积温
        self.thermal_time += thermal_time_today
        
        # 获取当前阶段和阶段列表
        current_stage = self.plant_state.phenological_stage
        stages = list(self.phenology_stages.keys())
        current_index = stages.index(current_stage)
        
        # 如果不是最后一个阶段，检查是否满足下一阶段的积温要求
        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            if self.thermal_time >= self.phenology_stages[next_stage]:
                self.plant_state.phenological_stage = next_stage


# ============================================================================
# 以下为辅助方法和主程序
# ============================================================================
# （完整代码见 cropgro-strawberry-implementation.py）

if __name__ == "__main__":
    """
    主程序：运行示例模拟
    """
    print("=" * 60)
    print("CROPGRO-Strawberry 草莓生长模型")
    print("核心源码（中文注释版）")
    print("=" * 60)
    print()
    print("本文件为带详细中文注释的核心源码版本。")
    print("完整可运行代码请参见：cropgro-strawberry-implementation.py")
    print()
    print("如需运行完整模拟，请执行：")
    print("  python cropgro-strawberry-implementation.py")
    print()
