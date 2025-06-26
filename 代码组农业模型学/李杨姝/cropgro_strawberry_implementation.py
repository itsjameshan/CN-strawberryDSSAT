"""Python implementation of the CROPGRO-Strawberry crop growth model.

This module contains a simplified, purely Python implementation of the
CROPGRO strawberry model. 结构与原Fortran代码类似，但为可读性做了简化。所有主要计算步骤都实现为小函数，并用@njit加速（可选）。
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dataclasses import dataclass
from numba import njit

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
    tavg = (tmin + tmax) / 2.0
    if tavg <= tbase:
        return 0.0
    elif tavg <= topt:
        return tavg - tbase
    elif tavg <= tmax_th:
        return (topt - tbase - (tavg - topt) * ((topt - tbase) / (tmax_th - topt)))
    else:
        return 0.0

@njit
def _photosynthesis(solar_radiation, tmax, tmin, rue, tbase, topt, k_light, lai, co2):
    tavg = (tmax + tmin) / 2.0
    if tavg <= tbase:
        temp_effect = 0.0
    elif tavg >= topt:
        temp_effect = 1.0
    else:
        temp_effect = (tavg - tbase) / (topt - tbase)
    co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)
    light_interception = 1.0 - np.exp(-k_light * lai)
    return (solar_radiation * rue * temp_effect * co2_effect * light_interception)

@njit
def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    tavg = (tmax + tmin) / 2.0
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)
    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    return et0 * kc

@njit
def _water_stress(field_capacity, wilting_point, root_depth, rainfall, transpiration):
    available_water = (field_capacity - wilting_point) * root_depth
    effective_rainfall = rainfall * 0.7
    deficit = max(0.0, transpiration - effective_rainfall)
    if deficit == 0.0:
        return 0.0
    else:
        stress_factor = min(1.0, deficit / available_water)
        return stress_factor

@njit
def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass, fruit_biomass, tmin, tmax):
    tavg = (tmin + tmax) / 2.0
    temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)
    resp_leaf = leaf_biomass * 0.03 * temp_factor
    resp_stem = stem_biomass * 0.015 * temp_factor
    resp_root = root_biomass * 0.01 * temp_factor
    resp_fruit = fruit_biomass * 0.01 * temp_factor
    return resp_leaf + resp_stem + resp_root + resp_fruit

class CropgroStrawberry:
    def __init__(self, latitude, planting_date, soil_properties, cultivar_params):
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        self.days_after_planting = 0
        self.plant_state = PlantState()
        self.thermal_time = 0.0
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
            self.plant_state.runner_number += (
                0.1 * self.plant_state.crown_number)
    def update_crowns(self):
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION', 'FLOWERING']:
            self.plant_state.crown_number += (
                0.02 * self.plant_state.crown_number)
    def update_fruits(self):
        stage = self.plant_state.phenological_stage
        if stage == 'FLOWERING':
            new_fruits = (self.cultivar['potential_fruits_per_crown'] * 
                          self.plant_state.crown_number * 0.1)
            self.plant_state.fruit_number += new_fruits
        elif stage == 'FRUIT_SET':
            new_fruits = (self.cultivar['potential_fruits_per_crown'] * 
                          self.plant_state.crown_number * 0.2)
            self.plant_state.fruit_number += new_fruits
    def simulate_day(self, weather_data):
        self.days_after_planting += 1
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
        day_of_year = current_date.timetuple().tm_yday
        daylength = self.calculate_daylength(day_of_year)
        thermal_time_today = self.calculate_thermal_time(
            weather_data['tmin'], weather_data['tmax'])
        self.update_phenology(thermal_time_today)
        photosynthesis = self.calculate_photosynthesis(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin']
        )
        transpiration = self.calculate_transpiration(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin'],
            weather_data['rh'],
            weather_data['wind_speed']
        )
        water_stress = self.calculate_water_stress(
            weather_data['rainfall'], transpiration)
        photosynthesis *= (1 - water_stress)
        plant_density = 5.0
        daily_biomass = photosynthesis / plant_density
        maintenance_resp = self.calculate_maintenance_respiration(
            weather_data['tmin'], weather_data['tmax'])
        daily_biomass = max(0, daily_biomass - maintenance_resp)
        self.partition_biomass(daily_biomass)
        self.update_runners()
        self.update_crowns()
        self.update_fruits()
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
        field_capacity = self.soil['field_capacity']
        wilting_point = self.soil['wilting_point']
        root_depth = self.plant_state.root_depth / 100.0
        return _water_stress(field_capacity, wilting_point, root_depth, rainfall, transpiration)
    def calculate_maintenance_respiration(self, tmin, tmax):
        return _maintenance_resp(
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            self.plant_state.fruit_biomass,
            tmin,
            tmax,
        )
    def simulate_growth(self, weather_data_df):
        self.results = []
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
            self.simulate_day(weather_day)
        self.results_df = pd.DataFrame(self.results)
        return self.results_df
    def plot_results(self):
        if not hasattr(self, 'results_df') or len(self.results_df) == 0:
            print("No simulation results to plot. Run simulate_growth() first.")
            return
        fig, axs = plt.subplots(3, 2, figsize=(14, 12))
        axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 'b-', label='Total')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['leaf_biomass'], 'g-', label='Leaf')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['stem_biomass'], 'k-', label='Stem')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['root_biomass'], 'r-', label='Root')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['fruit_biomass'], 'm-', label='Fruit')
        axs[0, 0].set_xlabel('Days After Planting')
        axs[0, 0].set_ylabel('Biomass (g/plant)')
        axs[0, 0].set_title('Plant Biomass')
        axs[0, 0].legend()
        axs[0, 1].plot(self.results_df['dap'], self.results_df['leaf_area_index'], 'g-')
        axs[0, 1].set_xlabel('Days After Planting')
        axs[0, 1].set_ylabel('LAI (m²/m²)')
        axs[0, 1].set_title('Leaf Area Index')
        axs[1, 0].plot(self.results_df['dap'], self.results_df['fruit_number'], 'm-')
        axs[1, 0].set_xlabel('Days After Planting')
        axs[1, 0].set_ylabel('Fruits (number/plant)')
        axs[1, 0].set_title('Fruit Number')
        axs[1, 1].plot(self.results_df['dap'], self.results_df['crown_number'], 'b-', label='Crowns')
        axs[1, 1].plot(self.results_df['dap'], self.results_df['runner_number'], 'r-', label='Runners')
        axs[1, 1].set_xlabel('Days After Planting')
        axs[1, 1].set_ylabel('Number per plant')
        axs[1, 1].set_title('Crowns and Runners')
        axs[1, 1].legend()
        axs[2, 0].plot(self.results_df['dap'], self.results_df['water_stress'], 'r-')
        axs[2, 0].set_xlabel('Days After Planting')
        axs[2, 0].set_ylabel('Water Stress (0-1)')
        axs[2, 0].set_title('Water Stress Factor')
        stages = list(self.phenology_stages.keys())
        stage_values = [stages.index(stage) for stage in self.results_df['stage']]
        axs[2, 1].plot(self.results_df['dap'], stage_values, 'b-')
        axs[2, 1].set_xlabel('Days After Planting')
        axs[2, 1].set_ylabel('Development Stage')
        axs[2, 1].set_yticks(range(len(stages)))
        axs[2, 1].set_yticklabels(stages)
        axs[2, 1].set_title('Phenological Development')
        plt.tight_layout()
        return fig

def run_example_simulation():
    soil_properties = {
        'max_root_depth': 50.0,
        'field_capacity': 200.0,
        'wilting_point': 50.0,
    }
    cultivar_params = {
        'name': 'Albion',
        'tbase': 4.0,
        'topt': 22.0,
        'tmax_th': 35.0,
        'rue': 2.5,
        'k_light': 0.6,
        'sla': 0.02,
        'potential_fruits_per_crown': 10.0
    }
    start_date = '2023-05-01'
    end_date = '2023-10-31'
    dates = pd.date_range(start=start_date, end=end_date)
    n_days = len(dates)
    np.random.seed(42)
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    seasonal_component = 10 * np.sin(2 * np.pi * (day_of_year - 172) / 365)
    tmax = 25.0 + seasonal_component + np.random.normal(0, 3, n_days)
    tmin = 10.0 + seasonal_component + np.random.normal(0, 2, n_days)
    solar_rad = (15.0 + 10.0 * np.sin(2 * np.pi * (day_of_year - 172) / 365) 
                + np.random.normal(0, 2, n_days))
    solar_rad = np.maximum(1.0, solar_rad)
    rainfall = np.zeros(n_days)
    rain_events = np.random.rand(n_days) < 0.3
    rainfall[rain_events] = np.random.exponential(5, np.sum(rain_events))
    rh = 70.0 + np.random.normal(0, 10, n_days)
    rh = np.clip(rh, 20, 100)
    wind_speed = 2.0 + np.random.exponential(1, n_days)
    weather_df = pd.DataFrame({
        'date': [d.strftime('%Y-%m-%d') for d in dates],
        'tmax': tmax,
        'tmin': tmin,
        'solar_radiation': solar_rad,
        'rainfall': rainfall,
        'rh': rh,
        'wind_speed': wind_speed
    })
    model = CropgroStrawberry(
        latitude=40.0,
        planting_date=start_date,
        soil_properties=soil_properties,
        cultivar_params=cultivar_params
    )
    results = model.simulate_growth(weather_df)
    fig = model.plot_results()
    return model, results, fig

if __name__ == "__main__":
    model, results, fig = run_example_simulation()
    print(f"Final biomass: {results['biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final fruit biomass: {results['fruit_biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final leaf area index: {results['leaf_area_index'].iloc[-1]:.2f} m²/m²")
    print(f"Final phenological stage: {results['stage'].iloc[-1]}")
    plt.show() 