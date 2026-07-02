"""Python implementation of the CROPGRO-Strawberry crop growth model.
This module contains a simplified, purely Python implementation of the
CROPGRO strawberry model.  The structure mirrors the original Fortran
code but trades some complexity for readability.  All major calculation
steps are implemented as small functions decorated with ``@njit`` to keep
them fast when the optional ``numba`` dependency is available.
"""
# CROPGRO-Strawberry Model Implementation in Python
# This is a simplified implementation of the CROPGRO model for strawberries
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from dataclasses import dataclass, asdict
from numba import njit

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

@dataclass
class PlantState:
    biomass: float = 0.0
    leaf_area_index: float = 0.1
    root_depth: float = 5.0
    fruit_number: float = 0.0
    fruit_biomass: float = 0.0
    leaf_biomass: float = 0.0
    stem_biomass: float = 0.0
    root_biomass: float = 0.0
    phenological_stage: str = "GERMINATION"
    development_rate: float = 0.0
    crown_number: float = 1.0
    runner_number: float = 0.0

@njit
def _calc_daylength(latitude, day_of_year):
    """Return length of the day in hours for a given latitude and date."""
    declination = 23.45 * np.sin(np.deg2rad(360 * (day_of_year - 80) / 365))
    lat_rad = np.deg2rad(latitude)
    term = -np.tan(lat_rad) * np.tan(np.deg2rad(declination))
    if term >= 1.0:
        return 0.0
    elif term <= -1.0:
        return 24.0
    else:
        return 24.0 * np.arccos(term) / np.pi

@njit
def _thermal_time(tmin, tmax, tbase, topt, tmax_th):
    """Calculate thermal time accumulation for a single day."""
    tavg = (tmin + tmax) / 2.0
    if tavg <= tbase:
        return 0.0
    elif tavg <= topt:
        return tavg - tbase
    elif tavg <= tmax_th:
        return (topt - tbase - (tavg - topt) * 
                ((topt - tbase) / (tmax_th - topt)))
    else:
        return 0.0

@njit
def _photosynthesis(solar_radiation, tmax, tmin, rue, tbase, topt, 
                    k_light, lai, co2):
    """Estimate daily photosynthesis based on temperature and light."""
    tavg = (tmax + tmin) / 2.0
    if tavg <= tbase:
        temp_effect = 0.0
    elif tavg >= topt:
        temp_effect = 1.0
    else:
        temp_effect = (tavg - tbase) / (topt - tbase)
    co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)
    light_interception = 1.0 - np.exp(-k_light * lai)
    return (solar_radiation * rue * temp_effect * co2_effect * 
            light_interception)

@njit
def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    """Compute potential plant transpiration using a simple ET0 approach."""
    tavg = (tmax + tmin) / 2.0
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)
    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    return et0 * kc

@njit
def _water_stress(field_capacity, wilting_point, root_depth, rainfall, 
                  transpiration):
    """Derive a water stress factor from soil moisture balance."""
    available_water = (field_capacity - wilting_point) * root_depth
    effective_rainfall = rainfall * 0.7
    deficit = max(0.0, transpiration - effective_rainfall)
    if deficit == 0.0:
        return 0.0
    else:
        stress_factor = min(1.0, deficit / available_water)
        return stress_factor

@njit
def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass, 
                      fruit_biomass, tmin, tmax):
    """Calculate maintenance respiration of all plant organs."""
    tavg = (tmin + tmax) / 2.0
    temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)
    resp_leaf = leaf_biomass * 0.03 * temp_factor
    resp_stem = stem_biomass * 0.015 * temp_factor
    resp_root = root_biomass * 0.01 * temp_factor
    resp_fruit = fruit_biomass * 0.01 * temp_factor
    return resp_leaf + resp_stem + resp_root + resp_fruit

class CropgroStrawberry:
    """
    A Python implementation of the CROPGRO-Strawberry crop model.
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
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        
        self.days_after_planting = 0
        self.plant_state = PlantState()
        self.thermal_time = 0.0
        
        self.phenology_stages = {
            'GERMINATION': 0,
            'EMERGENCE': 30,
            'JUVENILE': 60, 
            'VEGETATIVE': 100,
            'FLORAL_INDUCTION': 150,
            'FLOWERING': 200,
            'FRUIT_SET': 250,
            'FRUIT_DEVELOPMENT': 300,
            'FRUIT_MATURITY': 450,
            'SENESCENCE': 600
        }
        
        self.results = []
        
    def calculate_daylength(self, day_of_year):
        return _calc_daylength(self.latitude, day_of_year)
    
    def calculate_thermal_time(self, tmin, tmax):
        tbase = self.cultivar['tbase']
        topt = self.cultivar['topt']
        tmax_th = self.cultivar['tmax_th']
        return _thermal_time(tmin, tmax, tbase, topt, tmax_th)
    
    def update_phenology(self, thermal_time_today):
        self.thermal_time += thermal_time_today
        current_stage = self.plant_state.phenological_stage
        stages = list(self.phenology_stages.keys())
        current_index = stages.index(current_stage)
        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            if self.thermal_time >= self.phenology_stages[next_stage]:
                self.plant_state.phenological_stage = next_stage
    
    def calculate_photosynthesis(self, solar_radiation, tmax, tmin, co2=400):
        rue = self.cultivar['rue']
        lai = self.plant_state.leaf_area_index
        return _photosynthesis(
            solar_radiation, tmax, tmin, rue,
            self.cultivar['tbase'], self.cultivar['topt'],
            self.cultivar['k_light'], lai, co2
        )
    
    def calculate_transpiration(self, solar_radiation, tmax, tmin, rh, wind_speed):
        lai = self.plant_state.leaf_area_index
        base_transpiration = _transpiration(solar_radiation, tmax, tmin, rh, lai)
        wind_modifier = 1.0 + 0.1 * (wind_speed - 2.0)
        wind_modifier = max(0.5, min(2.0, wind_modifier))
        return base_transpiration * wind_modifier
    
    def partition_biomass(self, daily_biomass):
        stage = self.plant_state.phenological_stage
        if stage in ['GERMINATION', 'EMERGENCE', 'JUVENILE']:
            root_fraction = 0.4
            leaf_fraction = 0.4
            stem_fraction = 0.2
            fruit_fraction = 0.0
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
        else:
            root_fraction = 0.0
            leaf_fraction = 0.0
            stem_fraction = 0.0
            fruit_fraction = 0.0
        self.plant_state.root_biomass += daily_biomass * root_fraction
        self.plant_state.leaf_biomass += daily_biomass * leaf_fraction
        self.plant_state.stem_biomass += daily_biomass * stem_fraction
        self.plant_state.fruit_biomass += daily_biomass * fruit_fraction
        self.plant_state.biomass = (
            self.plant_state.root_biomass
            + self.plant_state.leaf_biomass
            + self.plant_state.stem_biomass
            + self.plant_state.fruit_biomass
        )
        sla = self.cultivar['sla']
        if stage in ['FRUIT_DEVELOPMENT', 'FRUIT_MATURITY', 'SENESCENCE']:
            sla *= 0.8
        self.plant_state.leaf_area_index = self.plant_state.leaf_biomass * sla
        max_root_growth_rate = 0.5
        max_root_depth = self.soil['max_root_depth']
        potential_root_growth = max_root_growth_rate * root_fraction
        current_root_depth = self.plant_state.root_depth
        if current_root_depth < max_root_depth:
            self.plant_state.root_depth = min(
                current_root_depth + potential_root_growth, max_root_depth)
    
    def update_runners(self):
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            self.plant_state.runner_number += 0.1 * self.plant_state.crown_number
    
    def update_crowns(self):
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION', 'FLOWERING']:
            self.plant_state.crown_number += 0.02 * self.plant_state.crown_number
    
    def update_fruits(self):
        stage = self.plant_state.phenological_stage
        if stage == 'FLOWERING':
            new_fruits = self.cultivar['potential_fruits_per_crown'] * self.plant_state.crown_number * 0.1
            self.plant_state.fruit_number += new_fruits
        elif stage == 'FRUIT_SET':
            new_fruits = self.cultivar['potential_fruits_per_crown'] * self.plant_state.crown_number * 0.2
            self.plant_state.fruit_number += new_fruits
    
    def simulate_day(self, weather_data):
        """
        Simulate one day of strawberry growth.
        
        Parameters:
        -----------
        weather_data : dict
            Dictionary containing weather data for the day:
            - tmax: Maximum temperature (°C)
            - tmin: Minimum temperature (°C)
            - solar_radiation: Solar radiation (MJ/m²)
            - rainfall: Rainfall (mm)
            - rh: Relative humidity (%)
            - wind_speed: Wind speed (m/s)
        """
        tmax = weather_data['tmax']
        tmin = weather_data['tmin']
        solar_radiation = weather_data['solar_radiation']
        rainfall = weather_data['rainfall']
        rh = weather_data['rh']
        wind_speed = weather_data['wind_speed']
        
        day_of_year = (self.planting_date + timedelta(days=self.days_after_planting)).timetuple().tm_yday
        
        thermal_time_today = self.calculate_thermal_time(tmin, tmax)
        self.update_phenology(thermal_time_today)
        
        photosynthesis = self.calculate_photosynthesis(solar_radiation, tmax, tmin)
        
        transpiration = self.calculate_transpiration(solar_radiation, tmax, tmin, rh, wind_speed)
        
        water_stress = _water_stress(
            self.soil['field_capacity'],
            self.soil['wilting_point'],
            self.plant_state.root_depth,
            rainfall,
            transpiration
        )
        
        maint_resp = _maintenance_resp(
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            self.plant_state.fruit_biomass,
            tmin,
            tmax
        )
        
        daily_biomass = max(0.0, photosynthesis * (1.0 - water_stress) - maint_resp)
        self.partition_biomass(daily_biomass)
        
        self.update_runners()
        self.update_crowns()
        self.update_fruits()
        
        self.results.append({
            'day': self.days_after_planting,
            'date': self.planting_date + timedelta(days=self.days_after_planting),
            'biomass': self.plant_state.biomass,
            'leaf_biomass': self.plant_state.leaf_biomass,
            'stem_biomass': self.plant_state.stem_biomass,
            'root_biomass': self.plant_state.root_biomass,
            'fruit_biomass': self.plant_state.fruit_biomass,
            'leaf_area_index': self.plant_state.leaf_area_index,
            'root_depth': self.plant_state.root_depth,
            'fruit_number': self.plant_state.fruit_number,
            'crown_number': self.plant_state.crown_number,
            'runner_number': self.plant_state.runner_number,
            'phenological_stage': self.plant_state.phenological_stage,
            'thermal_time': self.thermal_time,
            'water_stress': water_stress
        })
        
        self.days_after_planting += 1

def generate_synthetic_weather(start_date, days, base_temp=15):
    """Generate synthetic weather data for simulation."""
    weather_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        day_of_year = date.timetuple().tm_yday
        
        seasonal_temp = 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        tmax = base_temp + seasonal_temp + np.random.normal(0, 3)
        tmin = tmax - 8 + np.random.normal(0, 2)
        
        solar_radiation = max(2, 25 - 10 * np.cos(2 * np.pi * day_of_year / 365) + np.random.normal(0, 5))
        rainfall = np.random.poisson(2) if np.random.random() < 0.3 else 0
        
        rh = 60 + np.random.normal(0, 15)
        wind_speed = 2 + np.random.normal(0, 1)
        
        weather_data.append({
            'date': date,
            'tmax': tmax,
            'tmin': tmin,
            'solar_radiation': solar_radiation,
            'rainfall': rainfall,
            'rh': rh,
            'wind_speed': wind_speed
        })
    return weather_data

if __name__ == '__main__':
    print("Starting CROPGRO-Strawberry simulation...")
    
    soil_properties = {
        'max_root_depth': 30.0,
        'field_capacity': 250.0,
        'wilting_point': 100.0
    }
    
    cultivar_params = {
        'tbase': 5.0,
        'topt': 20.0,
        'tmax_th': 35.0,
        'rue': 1.5,
        'k_light': 0.7,
        'sla': 0.02,
        'potential_fruits_per_crown': 10
    }
    
    model = CropgroStrawberry(
        latitude=30.5,
        planting_date='2024-09-01',
        soil_properties=soil_properties,
        cultivar_params=cultivar_params
    )
    
    start_date = datetime(2024, 9, 1)
    weather_data = generate_synthetic_weather(start_date, 180)
    
    print(f"Simulating {len(weather_data)} days of strawberry growth...")
    for day_data in weather_data:
        model.simulate_day(day_data)
    
    results_df = pd.DataFrame(model.results)
    
    print("\nSimulation completed!")
    print("Final plant state:")
    print(f"  Total biomass: {model.plant_state.biomass:.2f} g/plant")
    print(f"  Fruit biomass: {model.plant_state.fruit_biomass:.2f} g/plant")
    print(f"  Fruit number: {model.plant_state.fruit_number:.1f}")
    print(f"  Leaf area index: {model.plant_state.leaf_area_index:.2f}")
    print(f"  Root depth: {model.plant_state.root_depth:.1f} cm")
    print(f"  Phenological stage: {model.plant_state.phenological_stage}")
    print(f"  Accumulated thermal time: {model.thermal_time:.1f} degree-days")
    
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    plt.plot(results_df['day'], results_df['biomass'], label='总生物量')
    plt.plot(results_df['day'], results_df['fruit_biomass'], label='果实生物量')
    plt.xlabel('种植后天数')
    plt.ylabel('生物量 (g/株)')
    plt.title('生物量累积')
    plt.legend()
    
    plt.subplot(2, 2, 2)
    plt.plot(results_df['day'], results_df['leaf_area_index'])
    plt.xlabel('种植后天数')
    plt.ylabel('叶面积指数')
    plt.title('叶面积发展')
    
    plt.subplot(2, 2, 3)
    plt.plot(results_df['day'], results_df['fruit_number'])
    plt.xlabel('种植后天数')
    plt.ylabel('果实数量')
    plt.title('果实产量')
    
    plt.subplot(2, 2, 4)
    stages = results_df['phenological_stage'].astype('category').cat.codes
    plt.plot(results_df['day'], stages)
    plt.xlabel('种植后天数')
    plt.ylabel('物候阶段')
    plt.title('发育进程')
    
    plt.tight_layout()
    plt.savefig('strawberry_simulation_results.png')
    print("\n静态结果图已保存到 strawberry_simulation_results.png")
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    
    line1, = axes[0, 0].plot([], [], label='总生物量')
    line1_fruit, = axes[0, 0].plot([], [], label='果实生物量')
    axes[0, 0].set_xlabel('种植后天数')
    axes[0, 0].set_ylabel('生物量 (g/株)')
    axes[0, 0].set_title('生物量累积')
    axes[0, 0].legend()
    axes[0, 0].set_xlim(0, len(results_df))
    axes[0, 0].set_ylim(0, max(results_df['biomass']) * 1.1)
    
    line2, = axes[0, 1].plot([], [])
    axes[0, 1].set_xlabel('种植后天数')
    axes[0, 1].set_ylabel('叶面积指数')
    axes[0, 1].set_title('叶面积发展')
    axes[0, 1].set_xlim(0, len(results_df))
    axes[0, 1].set_ylim(0, max(results_df['leaf_area_index']) * 1.1)
    
    line3, = axes[1, 0].plot([], [])
    axes[1, 0].set_xlabel('种植后天数')
    axes[1, 0].set_ylabel('果实数量')
    axes[1, 0].set_title('果实产量')
    axes[1, 0].set_xlim(0, len(results_df))
    axes[1, 0].set_ylim(0, max(results_df['fruit_number']) * 1.1)
    
    line4, = axes[1, 1].plot([], [])
    axes[1, 1].set_xlabel('种植后天数')
    axes[1, 1].set_ylabel('物候阶段')
    axes[1, 1].set_title('发育进程')
    axes[1, 1].set_xlim(0, len(results_df))
    axes[1, 1].set_ylim(0, max(stages) + 1)
    
    plt.tight_layout()
    
    def update(frame):
        line1.set_data(results_df['day'][:frame], results_df['biomass'][:frame])
        line1_fruit.set_data(results_df['day'][:frame], results_df['fruit_biomass'][:frame])
        line2.set_data(results_df['day'][:frame], results_df['leaf_area_index'][:frame])
        line3.set_data(results_df['day'][:frame], results_df['fruit_number'][:frame])
        line4.set_data(results_df['day'][:frame], stages[:frame])
        return line1, line1_fruit, line2, line3, line4
    
    anim = FuncAnimation(fig, update, frames=len(results_df), interval=50, blit=True)
    try:
        anim.save('strawberry_simulation_animation.mp4', fps=10, extra_args=['-vcodec', 'libx264'])
    except TypeError:
        anim.save('strawberry_simulation_animation.gif', fps=10)
    print("动态演示动画已保存到 strawberry_simulation_animation.gif")