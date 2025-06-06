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
import matplotlib.pyplot as plt

from dataclasses import dataclass, asdict
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
    """Return length of the day in hours for a given latitude and date."""
    # Solar declination angle for the given day of year
    declination = 23.45 * np.sin(np.deg2rad(360 * (day_of_year - 80) / 365))

    # Convert latitude to radians for trig functions
    lat_rad = np.deg2rad(latitude)

    # Intermediate term of the daylength equation
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
    # Mean daily temperature
    tavg = (tmin + tmax) / 2.0
    if tavg <= tbase:
        return 0.0
    elif tavg <= topt:
        return tavg - tbase
    elif tavg <= tmax_th:
        return topt - tbase - (tavg - topt) * ((topt - tbase) / (tmax_th - topt))
    else:
        return 0.0


@njit
def _photosynthesis(solar_radiation, tmax, tmin, rue, tbase, topt, k_light, lai, co2):
    """Estimate daily photosynthesis based on temperature and light."""
    # Average temperature used for temperature response
    tavg = (tmax + tmin) / 2.0
    if tavg <= tbase:
        temp_effect = 0.0
    elif tavg >= topt:
        temp_effect = 1.0
    else:
        temp_effect = (tavg - tbase) / (topt - tbase)
    co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)
    light_interception = 1.0 - np.exp(-k_light * lai)
    return solar_radiation * rue * temp_effect * co2_effect * light_interception


@njit
def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    """Compute potential plant transpiration using a simple ET0 approach."""
    # Mean temperature for the day
    tavg = (tmax + tmin) / 2.0

    # Simplified reference evapotranspiration (Hargreaves)
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)

    # Crop coefficient as a function of canopy development
    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    return et0 * kc


@njit
def _water_stress(field_capacity, wilting_point, root_depth, rainfall, transpiration):
    """Derive a water stress factor from soil moisture balance."""
    # Total available soil water within the root zone
    available_water = (field_capacity - wilting_point) * root_depth

    # Assume some fraction of rainfall is effective in wetting the soil
    effective_rainfall = rainfall * 0.7

    # Water deficit is unmet transpiration demand
    deficit = max(0.0, transpiration - effective_rainfall)
    if deficit == 0.0:
        return 0.0
    else:
        stress_factor = min(1.0, deficit / available_water)
        return stress_factor


@njit
def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass, fruit_biomass, tmin, tmax):
    """Calculate maintenance respiration of all plant organs."""
    # Temperature dependence of respiration (Q10 model)
    tavg = (tmin + tmax) / 2.0
    temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)

    # Organ specific respiration rates
    resp_leaf = leaf_biomass * 0.03 * temp_factor
    resp_stem = stem_biomass * 0.015 * temp_factor
    resp_root = root_biomass * 0.01 * temp_factor
    resp_fruit = fruit_biomass * 0.01 * temp_factor
    return resp_leaf + resp_stem + resp_root + resp_fruit

class CropgroStrawberry:
    """
    A Python implementation of the CROPGRO-Strawberry crop model.
    
    This model simulates strawberry growth and development based on 
    environmental conditions, plant characteristics, and management practices.
    """
    
    def __init__(self, latitude, planting_date, soil_properties, cultivar_params):
        """
        Initialize the CROPGRO-Strawberry model.
        
        Parameters:
        -----------
        latitude : float
            Site latitude in decimal degrees
        planting_date : str
            Planting date in format 'YYYY-MM-DD'
        soil_properties : dict
            Dictionary containing soil properties (depth, texture, water holding capacity, etc.)
        cultivar_params : dict
            Dictionary containing cultivar-specific parameters
        """
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        
        # Initialize state variables
        self.days_after_planting = 0
        self.plant_state = PlantState()
        
        # Accumulated thermal time (degree-days)
        self.thermal_time = 0.0
        
        # Phenological stages and their thermal time requirements
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
        
        # Results storage
        self.results = []
        
    def calculate_daylength(self, day_of_year):
        """
        Calculate daylength based on latitude and day of year.
        
        Parameters:
        -----------
        day_of_year : int
            Day of year (1-366)
            
        Returns:
        --------
        float
            Daylength in hours
        """
        return _calc_daylength(self.latitude, day_of_year)
    
    def calculate_thermal_time(self, tmin, tmax):
        """
        Calculate thermal time (degree-days) based on daily temperatures.
        
        Parameters:
        -----------
        tmin : float
            Minimum daily temperature (°C)
        tmax : float
            Maximum daily temperature (°C)
            
        Returns:
        --------
        float
            Thermal time accumulation for the day (degree-days)
        """
        tbase = self.cultivar['tbase']  # Base temperature
        topt = self.cultivar['topt']    # Optimal temperature
        tmax_th = self.cultivar['tmax_th']  # Maximum threshold temperature
        
        return _thermal_time(tmin, tmax, tbase, topt, tmax_th)
    
    def update_phenology(self, thermal_time_today):
        """
        Update plant phenological stage based on accumulated thermal time.
        
        Parameters:
        -----------
        thermal_time_today : float
            Thermal time accumulated for the current day
        """
        # Add today's heat units to the running total
        self.thermal_time += thermal_time_today
        
        # Determine if the plant should progress to the next stage
        current_stage = self.plant_state.phenological_stage
        stages = list(self.phenology_stages.keys())
        current_index = stages.index(current_stage)

        # If not at the last stage and thermal time exceeds threshold for next stage
        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            if self.thermal_time >= self.phenology_stages[next_stage]:
                self.plant_state.phenological_stage = next_stage
    
    def calculate_photosynthesis(self, solar_radiation, tmax, tmin, co2=400):
        """
        Calculate daily photosynthesis rate.
        
        Parameters:
        -----------
        solar_radiation : float
            Daily solar radiation (MJ/m²)
        tmax : float
            Maximum daily temperature (°C)
        tmin : float
            Minimum daily temperature (°C)
        co2 : float, optional
            Atmospheric CO2 concentration (ppm)
            
        Returns:
        --------
        float
            Daily photosynthesis rate (g CH2O/m²)
        """
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
        """
        Calculate plant transpiration using a simplified Penman-Monteith approach.
        
        Parameters:
        -----------
        solar_radiation : float
            Daily solar radiation (MJ/m²)
        tmax : float
            Maximum daily temperature (°C)
        tmin : float
            Minimum daily temperature (°C)
        rh : float
            Relative humidity (%)
        wind_speed : float
            Wind speed (m/s)
            
        Returns:
        --------
        float
            Daily transpiration (mm)
        """
        lai = self.plant_state.leaf_area_index
        return _transpiration(solar_radiation, tmax, tmin, rh, lai)
    
    def partition_biomass(self, daily_biomass):
        """
        Partition new biomass to plant organs based on development stage.
        
        Parameters:
        -----------
        daily_biomass : float
            Daily biomass production (g/plant)
        """
        # Determine partitioning fractions based on current stage
        stage = self.plant_state.phenological_stage
        
        # Partition coefficients change with development stage
        if stage in ['GERMINATION', 'EMERGENCE', 'JUVENILE']:
            # Early growth focuses on roots and leaves
            root_fraction = 0.4
            leaf_fraction = 0.4
            stem_fraction = 0.2
            fruit_fraction = 0.0
        elif stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            # Vegetative growth period
            root_fraction = 0.2
            leaf_fraction = 0.5
            stem_fraction = 0.3
            fruit_fraction = 0.0
        elif stage == 'FLOWERING':
            # Transition to reproductive growth
            root_fraction = 0.1
            leaf_fraction = 0.4
            stem_fraction = 0.3
            fruit_fraction = 0.2
        elif stage in ['FRUIT_SET', 'FRUIT_DEVELOPMENT']:
            # Reproductive growth period
            root_fraction = 0.05
            leaf_fraction = 0.25
            stem_fraction = 0.2
            fruit_fraction = 0.5
        elif stage == 'FRUIT_MATURITY':
            # Fruit filling period
            root_fraction = 0.0
            leaf_fraction = 0.1
            stem_fraction = 0.1
            fruit_fraction = 0.8
        else:  # 'SENESCENCE'
            # End of cycle
            root_fraction = 0.0
            leaf_fraction = 0.0
            stem_fraction = 0.0
            fruit_fraction = 0.0
            
        # Add new biomass to each organ
        self.plant_state.root_biomass += daily_biomass * root_fraction
        self.plant_state.leaf_biomass += daily_biomass * leaf_fraction
        self.plant_state.stem_biomass += daily_biomass * stem_fraction
        self.plant_state.fruit_biomass += daily_biomass * fruit_fraction
        
        # Update total biomass
        self.plant_state.biomass = (
            self.plant_state.root_biomass
            + self.plant_state.leaf_biomass
            + self.plant_state.stem_biomass
            + self.plant_state.fruit_biomass
        )
        
        # Update leaf area index based on new leaf biomass
        # Specific leaf area (m²/g) may change with development
        sla = self.cultivar['sla']
        if stage in ['FRUIT_DEVELOPMENT', 'FRUIT_MATURITY', 'SENESCENCE']:
            sla *= 0.8  # Reduced SLA during later stages
            
        self.plant_state.leaf_area_index = self.plant_state.leaf_biomass * sla
        
        # Update root depth
        max_root_growth_rate = 0.5  # Maximum root growth rate (cm/day)
        max_root_depth = self.soil['max_root_depth']
        
        potential_root_growth = max_root_growth_rate * root_fraction
        current_root_depth = self.plant_state.root_depth
        
        if current_root_depth < max_root_depth:
            self.plant_state.root_depth = min(current_root_depth + potential_root_growth, max_root_depth)
    
    def update_runners(self):
        """Update the number of runners based on development stage and conditions."""
        # Runners are produced mainly during vigorous vegetative growth
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            # Runner production is highest during vegetative growth
            self.plant_state.runner_number += 0.1 * self.plant_state.crown_number
    
    def update_crowns(self):
        """Update the number of crowns based on development stage and conditions."""
        # Strawberry plants can branch into multiple crowns when growing actively
        if self.plant_state.phenological_stage in ['VEGETATIVE', 'FLORAL_INDUCTION', 'FLOWERING']:
            # Crown development
            self.plant_state.crown_number += 0.02 * self.plant_state.crown_number
    
    def update_fruits(self):
        """Update fruit number and individual fruit weight."""
        # Fruit initiation depends on current development stage
        stage = self.plant_state.phenological_stage
        
        # New fruit initiation during flowering and fruit set
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
            - date: Date in 'YYYY-MM-DD' format
        """
        # Increment the counter of days since planting
        self.days_after_planting += 1
        
        # Current date
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
        day_of_year = current_date.timetuple().tm_yday
        
        # Calculate astronomical daylength for the location
        daylength = self.calculate_daylength(day_of_year)
        
        # Daily degree-day accumulation
        thermal_time_today = self.calculate_thermal_time(weather_data['tmin'], weather_data['tmax'])
        
        # Advance phenological stage if thresholds are met
        self.update_phenology(thermal_time_today)
        
        # Gross daily photosynthetic production
        photosynthesis = self.calculate_photosynthesis(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin']
        )
        
        # Potential water loss through transpiration
        transpiration = self.calculate_transpiration(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin'],
            weather_data['rh'],
            weather_data['wind_speed']
        )
        
        # Water stress reduces photosynthesis if rainfall is insufficient
        water_stress = self.calculate_water_stress(weather_data['rainfall'], transpiration)
        
        # Reduce photosynthesis due to water stress
        photosynthesis *= (1 - water_stress)
        
        # Convert canopy assimilation to per-plant biomass
        # Assume a density of five plants per square metre
        plant_density = 5.0  # plants/m²
        daily_biomass = photosynthesis / plant_density
        
        # Subtract respiration costs from produced biomass
        maintenance_resp = self.calculate_maintenance_respiration(weather_data['tmin'], weather_data['tmax'])
        daily_biomass = max(0, daily_biomass - maintenance_resp)
        
        # Partition biomass to plant organs
        self.partition_biomass(daily_biomass)
        
        # Update runners, crowns, and fruits
        self.update_runners()
        self.update_crowns()
        self.update_fruits()
        
        # Store results for this day
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
        """
        Calculate water stress factor (0-1) based on soil water balance.
        
        Parameters:
        -----------
        rainfall : float
            Daily rainfall (mm)
        transpiration : float
            Potential transpiration (mm)
            
        Returns:
        --------
        float
            Water stress factor (0 = no stress, 1 = maximum stress)
        """
        field_capacity = self.soil['field_capacity']
        wilting_point = self.soil['wilting_point']
        root_depth = self.plant_state.root_depth / 100.0
        return _water_stress(field_capacity, wilting_point, root_depth, rainfall, transpiration)
    
    def calculate_maintenance_respiration(self, tmin, tmax):
        """
        Calculate maintenance respiration based on biomass and temperature.
        
        Parameters:
        -----------
        tmin : float
            Minimum daily temperature (°C)
        tmax : float
            Maximum daily temperature (°C)
            
        Returns:
        --------
        float
            Maintenance respiration (g/plant)
        """
        return _maintenance_resp(
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            self.plant_state.fruit_biomass,
            tmin,
            tmax,
        )
    
    def simulate_growth(self, weather_data_df):
        """
        Simulate strawberry growth for a period defined by the weather data.
        
        Parameters:
        -----------
        weather_data_df : pandas.DataFrame
            DataFrame containing daily weather data with the following columns:
            - date: Date in 'YYYY-MM-DD' format
            - tmax: Maximum temperature (°C)
            - tmin: Minimum temperature (°C)
            - solar_radiation: Solar radiation (MJ/m²)
            - rainfall: Rainfall (mm)
            - rh: Relative humidity (%)
            - wind_speed: Wind speed (m/s)
        """
        # Reset results
        self.results = []
        
        # Simulate each day using itertuples for speed
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
        
        # Convert results to DataFrame
        self.results_df = pd.DataFrame(self.results)
        return self.results_df
    
    def plot_results(self):
        """Plot key simulation results."""
        if not hasattr(self, 'results_df') or len(self.results_df) == 0:
            print("No simulation results to plot. Run simulate_growth() first.")
            return
        
        fig, axs = plt.subplots(3, 2, figsize=(14, 12))
        
        # Plot biomass
        axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 'b-', label='Total')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['leaf_biomass'], 'g-', label='Leaf')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['stem_biomass'], 'k-', label='Stem')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['root_biomass'], 'r-', label='Root')
        axs[0, 0].plot(self.results_df['dap'], self.results_df['fruit_biomass'], 'm-', label='Fruit')
        axs[0, 0].set_xlabel('Days After Planting')
        axs[0, 0].set_ylabel('Biomass (g/plant)')
        axs[0, 0].set_title('Plant Biomass')
        axs[0, 0].legend()
        
        # Plot LAI
        axs[0, 1].plot(self.results_df['dap'], self.results_df['leaf_area_index'], 'g-')
        axs[0, 1].set_xlabel('Days After Planting')
        axs[0, 1].set_ylabel('LAI (m²/m²)')
        axs[0, 1].set_title('Leaf Area Index')
        
        # Plot fruit number
        axs[1, 0].plot(self.results_df['dap'], self.results_df['fruit_number'], 'm-')
        axs[1, 0].set_xlabel('Days After Planting')
        axs[1, 0].set_ylabel('Fruits (number/plant)')
        axs[1, 0].set_title('Fruit Number')
        
        # Plot crowns and runners
        axs[1, 1].plot(self.results_df['dap'], self.results_df['crown_number'], 'b-', label='Crowns')
        axs[1, 1].plot(self.results_df['dap'], self.results_df['runner_number'], 'r-', label='Runners')
        axs[1, 1].set_xlabel('Days After Planting')
        axs[1, 1].set_ylabel('Number per plant')
        axs[1, 1].set_title('Crowns and Runners')
        axs[1, 1].legend()
        
        # Plot water stress
        axs[2, 0].plot(self.results_df['dap'], self.results_df['water_stress'], 'r-')
        axs[2, 0].set_xlabel('Days After Planting')
        axs[2, 0].set_ylabel('Water Stress (0-1)')
        axs[2, 0].set_title('Water Stress Factor')
        
        # Plot phenological development
        # Convert stages to numeric values for plotting
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


# Example usage of the CROPGRO-Strawberry model
def run_example_simulation():
    """Run the model with synthetic weather data and return results."""
    # Define soil properties
    soil_properties = {
        'max_root_depth': 50.0,  # cm
        'field_capacity': 200.0,  # mm/m
        'wilting_point': 50.0,   # mm/m
    }
    
    # Define cultivar parameters
    cultivar_params = {
        'name': 'Albion',
        'tbase': 4.0,       # Base temperature (°C)
        'topt': 22.0,       # Optimal temperature (°C)
        'tmax_th': 35.0,    # Maximum threshold temperature (°C)
        'rue': 2.5,         # Radiation use efficiency (g/MJ)
        'k_light': 0.6,     # Light extinction coefficient
        'sla': 0.02,        # Specific leaf area (m²/g)
        'potential_fruits_per_crown': 10.0  # Maximum fruits per crown
    }
    
    # Create a sample weather dataset
    start_date = '2023-05-01'
    end_date = '2023-10-31'
    
    dates = pd.date_range(start=start_date, end=end_date)
    n_days = len(dates)
    
    # Create synthetic weather data
    np.random.seed(42)  # For reproducibility
    
    # Temperature follows seasonal pattern
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    seasonal_component = 10 * np.sin(2 * np.pi * (day_of_year - 172) / 365)
    
    tmax = 25.0 + seasonal_component + np.random.normal(0, 3, n_days)
    tmin = 10.0 + seasonal_component + np.random.normal(0, 2, n_days)
    
    # Solar radiation follows seasonal pattern
    solar_rad = 15.0 + 10.0 * np.sin(2 * np.pi * (day_of_year - 172) / 365) + np.random.normal(0, 2, n_days)
    solar_rad = np.maximum(1.0, solar_rad)  # Ensure positive radiation
    
    # Rainfall - random events
    rainfall = np.zeros(n_days)
    rain_events = np.random.rand(n_days) < 0.3  # 30% chance of rain each day
    rainfall[rain_events] = np.random.exponential(5, np.sum(rain_events))
    
    # Relative humidity and wind speed
    rh = 70.0 + np.random.normal(0, 10, n_days)
    rh = np.clip(rh, 20, 100)  # Constrain to valid range
    
    wind_speed = 2.0 + np.random.exponential(1, n_days)
    
    # Create weather DataFrame
    weather_df = pd.DataFrame({
        'date': [d.strftime('%Y-%m-%d') for d in dates],
        'tmax': tmax,
        'tmin': tmin,
        'solar_radiation': solar_rad,
        'rainfall': rainfall,
        'rh': rh,
        'wind_speed': wind_speed
    })
    
    # Initialize model
    model = CropgroStrawberry(
        latitude=40.0,
        planting_date=start_date,
        soil_properties=soil_properties,
        cultivar_params=cultivar_params
    )
    
    # Run simulation
    results = model.simulate_growth(weather_df)
    
    # Plot results
    fig = model.plot_results()
    
    return model, results, fig


if __name__ == "__main__":
    # Run example simulation
    model, results, fig = run_example_simulation()
    
    # Display some results
    print(f"Final biomass: {results['biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final fruit biomass: {results['fruit_biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final leaf area index: {results['leaf_area_index'].iloc[-1]:.2f} m²/m²")
    print(f"Final phenological stage: {results['stage'].iloc[-1]}")
    
    # Show plot
    plt.show()
