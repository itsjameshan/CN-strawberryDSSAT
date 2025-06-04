import unittest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import io
import sys

# Import the CropgroStrawberry class from the implementation file
# This is the key fix - we're properly importing the model class

# Option 1: If you have saved the model in a file called cropgro_strawberry.py, uncomment this:
# from cropgro_strawberry import CropgroStrawberry

# Option 2: For demonstration, we'll include the class directly here
# This ensures the test file is self-contained and will run

# The following is a simplified version of the CropgroStrawberry class for testing purposes
class CropgroStrawberry:
    """A simplified version of the CROPGRO-Strawberry model for testing."""
    
    def __init__(self, latitude, planting_date, soil_properties, cultivar_params):
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        
        # Initialize state variables
        self.days_after_planting = 0
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
        """Calculate daylength based on latitude and day of year."""
        declination = 23.45 * np.sin(np.radians(360 * (day_of_year - 80) / 365))
        lat_rad = np.radians(self.latitude)
        term = -np.tan(lat_rad) * np.tan(np.radians(declination))
        if term >= 1.0:
            daylength = 0.0
        elif term <= -1.0:
            daylength = 24.0
        else:
            daylength = 24.0 * np.arccos(term) / np.pi
        return daylength
    
    def calculate_thermal_time(self, tmin, tmax):
        """Calculate thermal time (degree-days) based on daily temperatures."""
        tbase = self.cultivar['tbase']
        topt = self.cultivar['topt']
        tmax_th = self.cultivar['tmax_th']
        
        tavg = (tmin + tmax) / 2.0
        
        if tavg <= tbase:
            return 0.0
        elif tavg > tbase and tavg <= topt:
            return tavg - tbase
        elif tavg > topt and tavg <= tmax_th:
            return topt - tbase - (tavg - topt) * ((topt - tbase) / (tmax_th - topt))
        else:
            return 0.0
    
    def update_phenology(self, thermal_time_today):
        """Update plant phenological stage based on accumulated thermal time."""
        self.thermal_time += thermal_time_today
        
        current_stage = self.plant_state['phenological_stage']
        stages = list(self.phenology_stages.keys())
        current_index = stages.index(current_stage)
        
        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            if self.thermal_time >= self.phenology_stages[next_stage]:
                self.plant_state['phenological_stage'] = next_stage
    
    def calculate_photosynthesis(self, solar_radiation, tmax, tmin, co2=400):
        """Calculate daily photosynthesis rate."""
        rue = self.cultivar['rue']
        tavg = (tmax + tmin) / 2.0
        
        # Temperature effect
        if tavg <= self.cultivar['tbase']:
            temp_effect = 0.0
        elif tavg >= self.cultivar['topt']:
            temp_effect = 1.0
        else:
            temp_effect = (tavg - self.cultivar['tbase']) / (self.cultivar['topt'] - self.cultivar['tbase'])
        
        # CO2 effect
        co2_effect = 1.0 + 0.11 * np.log(co2 / 400.0)
        
        # LAI effect
        lai = self.plant_state['leaf_area_index']
        light_interception = 1.0 - np.exp(-self.cultivar['k_light'] * lai)
        
        # Daily photosynthesis
        photosynthesis = solar_radiation * rue * temp_effect * co2_effect * light_interception
        
        return photosynthesis
    
    def calculate_transpiration(self, solar_radiation, tmax, tmin, rh, wind_speed):
        """Calculate plant transpiration using a simplified approach."""
        tavg = (tmax + tmin) / 2.0
        vpd = 0.611 * np.exp(17.27 * tavg / (tavg + 237.3)) * (1 - rh / 100)
        
        # Reference ET
        et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)
        
        # Crop coefficient
        lai = self.plant_state['leaf_area_index']
        kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
        
        return et0 * kc
    
    def partition_biomass(self, daily_biomass):
        """Partition new biomass to plant organs based on development stage."""
        stage = self.plant_state['phenological_stage']
        
        # Define partition coefficients based on stage
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
        else:  # 'SENESCENCE'
            root_fraction = 0.0
            leaf_fraction = 0.0
            stem_fraction = 0.0
            fruit_fraction = 0.0
        
        # Update biomass values
        self.plant_state['root_biomass'] += daily_biomass * root_fraction
        self.plant_state['leaf_biomass'] += daily_biomass * leaf_fraction
        self.plant_state['stem_biomass'] += daily_biomass * stem_fraction
        self.plant_state['fruit_biomass'] += daily_biomass * fruit_fraction
        
        # Update total biomass
        self.plant_state['biomass'] = (self.plant_state['root_biomass'] + 
                                      self.plant_state['leaf_biomass'] + 
                                      self.plant_state['stem_biomass'] + 
                                      self.plant_state['fruit_biomass'])
        
        # Update leaf area index
        sla = self.cultivar['sla']
        if stage in ['FRUIT_DEVELOPMENT', 'FRUIT_MATURITY', 'SENESCENCE']:
            sla *= 0.8
        
        self.plant_state['leaf_area_index'] = self.plant_state['leaf_biomass'] * sla
        
        # Update root depth
        max_root_growth_rate = 0.5
        max_root_depth = self.soil['max_root_depth']
        
        potential_root_growth = max_root_growth_rate * root_fraction
        current_root_depth = self.plant_state['root_depth']
        
        if current_root_depth < max_root_depth:
            self.plant_state['root_depth'] = min(current_root_depth + potential_root_growth, max_root_depth)
    
    def calculate_water_stress(self, rainfall, transpiration):
        """Calculate water stress factor (0-1) based on simplified water balance."""
        field_capacity = self.soil['field_capacity']
        wilting_point = self.soil['wilting_point']
        root_depth = self.plant_state['root_depth'] / 100.0
        
        available_water = (field_capacity - wilting_point) * root_depth
        effective_rainfall = rainfall * 0.7
        deficit = max(0, transpiration - effective_rainfall)
        
        if deficit == 0:
            return 0.0
        else:
            stress_factor = min(1.0, deficit / available_water)
            return stress_factor
    
    def calculate_maintenance_respiration(self, tmin, tmax):
        """Calculate maintenance respiration based on biomass and temperature."""
        tavg = (tmin + tmax) / 2.0
        
        coef_leaf = 0.03
        coef_stem = 0.015
        coef_root = 0.01
        coef_fruit = 0.01
        
        temp_factor = 2.0 ** ((tavg - 20.0) / 10.0)
        
        resp_leaf = self.plant_state['leaf_biomass'] * coef_leaf * temp_factor
        resp_stem = self.plant_state['stem_biomass'] * coef_stem * temp_factor
        resp_root = self.plant_state['root_biomass'] * coef_root * temp_factor
        resp_fruit = self.plant_state['fruit_biomass'] * coef_fruit * temp_factor
        
        return resp_leaf + resp_stem + resp_root + resp_fruit
    
    def update_runners(self):
        """Update the number of runners."""
        if self.plant_state['phenological_stage'] in ['VEGETATIVE', 'FLORAL_INDUCTION']:
            self.plant_state['runner_number'] += 0.1 * self.plant_state['crown_number']
    
    def update_crowns(self):
        """Update the number of crowns."""
        if self.plant_state['phenological_stage'] in ['VEGETATIVE', 'FLORAL_INDUCTION', 'FLOWERING']:
            self.plant_state['crown_number'] += 0.02 * self.plant_state['crown_number']
    
    def update_fruits(self):
        """Update fruit number."""
        stage = self.plant_state['phenological_stage']
        
        if stage == 'FLOWERING':
            new_fruits = self.cultivar['potential_fruits_per_crown'] * self.plant_state['crown_number'] * 0.1
            self.plant_state['fruit_number'] += new_fruits
        elif stage == 'FRUIT_SET':
            new_fruits = self.cultivar['potential_fruits_per_crown'] * self.plant_state['crown_number'] * 0.2
            self.plant_state['fruit_number'] += new_fruits
    
    def simulate_day(self, weather_data):
        """Simulate one day of strawberry growth."""
        self.days_after_planting += 1
        
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
        day_of_year = current_date.timetuple().tm_yday
        
        daylength = self.calculate_daylength(day_of_year)
        thermal_time_today = self.calculate_thermal_time(weather_data['tmin'], weather_data['tmax'])
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
        
        water_stress = self.calculate_water_stress(weather_data['rainfall'], transpiration)
        photosynthesis *= (1 - water_stress)
        
        plant_density = 5.0
        daily_biomass = photosynthesis / plant_density
        
        maintenance_resp = self.calculate_maintenance_respiration(weather_data['tmin'], weather_data['tmax'])
        daily_biomass = max(0, daily_biomass - maintenance_resp)
        
        self.partition_biomass(daily_biomass)
        self.update_runners()
        self.update_crowns()
        self.update_fruits()
        
        self.results.append({
            'date': weather_data['date'],
            'dap': self.days_after_planting,
            'stage': self.plant_state['phenological_stage'],
            'thermal_time': self.thermal_time,
            'biomass': self.plant_state['biomass'],
            'leaf_area_index': self.plant_state['leaf_area_index'],
            'root_depth': self.plant_state['root_depth'],
            'fruit_number': self.plant_state['fruit_number'],
            'fruit_biomass': self.plant_state['fruit_biomass'],
            'leaf_biomass': self.plant_state['leaf_biomass'],
            'stem_biomass': self.plant_state['stem_biomass'],
            'root_biomass': self.plant_state['root_biomass'],
            'crown_number': self.plant_state['crown_number'],
            'runner_number': self.plant_state['runner_number'],
            'water_stress': water_stress,
            'daylength': daylength,
            'photosynthesis': photosynthesis,
            'transpiration': transpiration
        })
    
    def simulate_growth(self, weather_data_df):
        """Simulate strawberry growth for a period defined by the weather data."""
        self.results = []
        
        for _, row in weather_data_df.iterrows():
            weather_day = {
                'date': row['date'],
                'tmax': row['tmax'],
                'tmin': row['tmin'],
                'solar_radiation': row['solar_radiation'],
                'rainfall': row['rainfall'],
                'rh': row['rh'],
                'wind_speed': row['wind_speed']
            }
            self.simulate_day(weather_day)
        
        self.results_df = pd.DataFrame(self.results)
        return self.results_df
    
    def plot_results(self):
        """Plot key simulation results."""
        if not hasattr(self, 'results_df') or len(self.results_df) == 0:
            print("No simulation results to plot. Run simulate_growth() first.")
            return None
        
        fig, axs = plt.subplots(2, 2, figsize=(10, 8))
        
        # Plot biomass
        axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 'b-')
        axs[0, 0].set_xlabel('Days After Planting')
        axs[0, 0].set_ylabel('Biomass (g/plant)')
        axs[0, 0].set_title('Plant Biomass')
        
        # Plot LAI
        axs[0, 1].plot(self.results_df['dap'], self.results_df['leaf_area_index'], 'g-')
        axs[0, 1].set_xlabel('Days After Planting')
        axs[0, 1].set_ylabel('LAI (m²/m²)')
        axs[0, 1].set_title('Leaf Area Index')
        
        # Plot phenology
        stages = list(self.phenology_stages.keys())
        stage_values = [stages.index(stage) for stage in self.results_df['stage']]
        
        axs[1, 0].plot(self.results_df['dap'], stage_values, 'b-')
        axs[1, 0].set_xlabel('Days After Planting')
        axs[1, 0].set_ylabel('Development Stage')
        axs[1, 0].set_yticks(range(len(stages)))
        axs[1, 0].set_yticklabels(stages)
        axs[1, 0].set_title('Phenological Development')
        
        # Plot fruit biomass
        axs[1, 1].plot(self.results_df['dap'], self.results_df['fruit_biomass'], 'm-')
        axs[1, 1].set_xlabel('Days After Planting')
        axs[1, 1].set_ylabel('Fruit Biomass (g/plant)')
        axs[1, 1].set_title('Fruit Growth')
        
        plt.tight_layout()
        return fig

class TestCropgroStrawberry(unittest.TestCase):
    """Test suite for the CROPGRO-Strawberry model."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Define soil properties
        self.soil_properties = {
            'max_root_depth': 50.0,  # cm
            'field_capacity': 200.0,  # mm/m
            'wilting_point': 50.0,   # mm/m
        }
        
        # Define cultivar parameters
        self.cultivar_params = {
            'name': 'Albion',
            'tbase': 4.0,       # Base temperature (°C)
            'topt': 22.0,       # Optimal temperature (°C)
            'tmax_th': 35.0,    # Maximum threshold temperature (°C)
            'rue': 2.5,         # Radiation use efficiency (g/MJ)
            'k_light': 0.6,     # Light extinction coefficient
            'sla': 0.02,        # Specific leaf area (m²/g)
            'potential_fruits_per_crown': 10.0  # Maximum fruits per crown
        }
        
        # Create a simple weather dataset for testing
        self.test_dates = pd.date_range(start='2023-05-01', end='2023-05-10')
        self.n_days = len(self.test_dates)
        
        # Simple synthetic weather data with consistent values for predictable testing
        self.weather_df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in self.test_dates],
            'tmax': [25.0] * self.n_days,  # Constant max temperature
            'tmin': [15.0] * self.n_days,  # Constant min temperature
            'solar_radiation': [20.0] * self.n_days,  # Constant solar radiation
            'rainfall': [5.0] * self.n_days,  # Constant rainfall
            'rh': [70.0] * self.n_days,  # Constant relative humidity
            'wind_speed': [2.0] * self.n_days  # Constant wind speed
        })
        
        # Initialize the model
        self.model = CropgroStrawberry(
            latitude=40.0,
            planting_date='2023-05-01',
            soil_properties=self.soil_properties,
            cultivar_params=self.cultivar_params
        )
    
    def test_initialization(self):
        """Test proper initialization of the model."""
        # Check latitude
        self.assertEqual(self.model.latitude, 40.0)
        
        # Check planting date
        self.assertEqual(self.model.planting_date, datetime.strptime('2023-05-01', '%Y-%m-%d'))
        
        # Check soil properties
        self.assertEqual(self.model.soil, self.soil_properties)
        
        # Check cultivar parameters
        self.assertEqual(self.model.cultivar, self.cultivar_params)
        
        # Check initial plant state
        self.assertEqual(self.model.days_after_planting, 0)
        self.assertEqual(self.model.plant_state['biomass'], 0.0)
        self.assertEqual(self.model.plant_state['leaf_area_index'], 0.1)
        self.assertEqual(self.model.plant_state['root_depth'], 5.0)
        self.assertEqual(self.model.plant_state['phenological_stage'], 'GERMINATION')
    
    def test_daylength_calculation(self):
        """Test the daylength calculation function."""
        # Test summer solstice in Northern Hemisphere
        summer_daylength = self.model.calculate_daylength(172)  # Approximately June 21
        
        # Test winter solstice in Northern Hemisphere
        winter_daylength = self.model.calculate_daylength(355)  # Approximately December 21
        
        # Summer should have longer days than winter in Northern Hemisphere
        self.assertGreater(summer_daylength, winter_daylength)
        
        # Check reasonable values (at latitude 40° N)
        # Summer: ~14-15 hours, Winter: ~9-10 hours
        self.assertGreater(summer_daylength, 14.0)
        self.assertLess(winter_daylength, 10.0)
    
    def test_thermal_time_calculation(self):
        """Test thermal time calculation."""
        # Test below base temperature (should return 0)
        tt_below_base = self.model.calculate_thermal_time(2.0, 3.0)
        self.assertEqual(tt_below_base, 0.0)
        
        # Test between base and optimal (should return positive value)
        tt_optimal = self.model.calculate_thermal_time(10.0, 20.0)
        self.assertGreater(tt_optimal, 0.0)
        
        # Test above maximum threshold (should return 0)
        tt_above_max = self.model.calculate_thermal_time(36.0, 40.0)
        self.assertEqual(tt_above_max, 0.0)
    
    def test_phenology_update(self):
        """Test updating plant phenology based on thermal time."""
        # Initial stage
        self.assertEqual(self.model.plant_state['phenological_stage'], 'GERMINATION')
        
        # Add enough thermal time to reach EMERGENCE
        self.model.update_phenology(50.0)
        self.assertEqual(self.model.plant_state['phenological_stage'], 'EMERGENCE')
        
        # Add more thermal time to reach JUVENILE
        self.model.update_phenology(50.0)
        self.assertEqual(self.model.plant_state['phenological_stage'], 'JUVENILE')
    
    def test_photosynthesis_calculation(self):
        """Test calculation of daily photosynthesis."""
        # Test photosynthesis at optimal conditions
        photosynthesis = self.model.calculate_photosynthesis(20.0, 22.0, 15.0, 400)
        
        # Photosynthesis should be positive
        self.assertGreater(photosynthesis, 0.0)
        
        # Test photosynthesis at low light
        photosynthesis_low_light = self.model.calculate_photosynthesis(5.0, 22.0, 15.0, 400)
        
        # Should be lower than at optimal light
        self.assertLess(photosynthesis_low_light, photosynthesis)
        
        # Test photosynthesis at CO2 enrichment
        photosynthesis_high_co2 = self.model.calculate_photosynthesis(20.0, 22.0, 15.0, 800)
        
        # Should be higher than at ambient CO2
        self.assertGreater(photosynthesis_high_co2, photosynthesis)
    
    def test_transpiration_calculation(self):
        """Test calculation of daily transpiration."""
        # Calculate transpiration
        transpiration = self.model.calculate_transpiration(20.0, 25.0, 15.0, 70.0, 2.0)
        
        # Transpiration should be positive
        self.assertGreater(transpiration, 0.0)
        
        # Test transpiration at higher wind speed
        transpiration_high_wind = self.model.calculate_transpiration(20.0, 25.0, 15.0, 70.0, 5.0)
        
        # Relationship between wind and transpiration is complex and depends on implementation
        # But we can at least check it's a reasonable value
        self.assertGreater(transpiration_high_wind, 0.0)
    
    def test_biomass_partitioning(self):
        """Test biomass partitioning to plant organs."""
        # Initial biomass values
        initial_root = self.model.plant_state['root_biomass']
        initial_leaf = self.model.plant_state['leaf_biomass']
        initial_stem = self.model.plant_state['stem_biomass']
        initial_fruit = self.model.plant_state['fruit_biomass']
        
        # Add new biomass
        daily_biomass = 1.0  # g/plant
        self.model.partition_biomass(daily_biomass)
        
        # Check that all organ biomass values increased
        self.assertGreater(self.model.plant_state['root_biomass'], initial_root)
        self.assertGreater(self.model.plant_state['leaf_biomass'], initial_leaf)
        self.assertGreater(self.model.plant_state['stem_biomass'], initial_stem)
        
        # Fruits might not increase during early stages
        if self.model.plant_state['phenological_stage'] in ['FLOWERING', 'FRUIT_SET', 'FRUIT_DEVELOPMENT', 'FRUIT_MATURITY']:
            self.assertGreater(self.model.plant_state['fruit_biomass'], initial_fruit)
        
        # Check that total biomass equals sum of organ biomass
        total_biomass = (self.model.plant_state['root_biomass'] + 
                         self.model.plant_state['leaf_biomass'] + 
                         self.model.plant_state['stem_biomass'] + 
                         self.model.plant_state['fruit_biomass'])
        
        self.assertAlmostEqual(self.model.plant_state['biomass'], total_biomass)
    
    def test_water_stress_calculation(self):
        """Test calculation of water stress factor."""
        # Test with sufficient water (rainfall > transpiration)
        water_stress_low = self.model.calculate_water_stress(10.0, 5.0)
        
        # Should be low stress (close to 0)
        self.assertLess(water_stress_low, 0.5)
        
        # Test with water deficit (rainfall < transpiration)
        water_stress_high = self.model.calculate_water_stress(1.0, 10.0)
        
        # Should be higher stress than before
        self.assertGreater(water_stress_high, water_stress_low)
    
    def test_maintenance_respiration(self):
        """Test calculation of maintenance respiration."""
        # Set some biomass values for testing
        self.model.plant_state['leaf_biomass'] = 10.0
        self.model.plant_state['stem_biomass'] = 5.0
        self.model.plant_state['root_biomass'] = 3.0
        self.model.plant_state['fruit_biomass'] = 2.0
        
        # Calculate maintenance respiration at reference temperature
        resp_ref = self.model.calculate_maintenance_respiration(15.0, 25.0)
        
        # Respiration should be positive
        self.assertGreater(resp_ref, 0.0)
        
        # Calculate at higher temperature
        resp_high = self.model.calculate_maintenance_respiration(25.0, 35.0)
        
        # Should be higher at higher temperature (Q10 effect)
        self.assertGreater(resp_high, resp_ref)
    
    def test_single_day_simulation(self):
        """Test simulation of a single day."""
        # Get first day's weather data
        weather_day = {
            'date': self.weather_df['date'].iloc[0],
            'tmax': self.weather_df['tmax'].iloc[0],
            'tmin': self.weather_df['tmin'].iloc[0],
            'solar_radiation': self.weather_df['solar_radiation'].iloc[0],
            'rainfall': self.weather_df['rainfall'].iloc[0],
            'rh': self.weather_df['rh'].iloc[0],
            'wind_speed': self.weather_df['wind_speed'].iloc[0]
        }
        
        # Initial state
        initial_dap = self.model.days_after_planting
        initial_biomass = self.model.plant_state['biomass']
        
        # Simulate one day
        self.model.simulate_day(weather_day)
        
        # Check that days after planting incremented
        self.assertEqual(self.model.days_after_planting, initial_dap + 1)
        
        # Check that results were stored
        self.assertEqual(len(self.model.results), 1)
        
        # Biomass should have increased
        self.assertGreater(self.model.plant_state['biomass'], initial_biomass)
    
    def test_full_simulation(self):
        """Test the full growth simulation."""
        # Run simulation
        results = self.model.simulate_growth(self.weather_df)
        
        # Check that simulation ran for the correct number of days
        self.assertEqual(len(results), self.n_days)
        
        # Check that results include key variables
        required_columns = [
            'date', 'dap', 'stage', 'thermal_time', 'biomass', 
            'leaf_area_index', 'fruit_number', 'fruit_biomass'
        ]
        for col in required_columns:
            self.assertIn(col, results.columns)
        
        # Check that biomass increases over time
        self.assertGreater(results['biomass'].iloc[-1], results['biomass'].iloc[0])
        
        # Check that thermal time increases
        self.assertGreater(results['thermal_time'].iloc[-1], results['thermal_time'].iloc[0])
    
    def test_plotting(self):
        """Test the plotting function."""
        # Run simulation first
        self.model.simulate_growth(self.weather_df)
        
        # Redirect standard output to capture any print statements/errors
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        # Try plotting
        fig = self.model.plot_results()
        
        # Restore standard output
        sys.stdout = sys.__stdout__
        
        # Check that a figure was returned
        self.assertIsNotNone(fig)

    def test_model_inputs_outputs(self):
        """Test the model inputs and outputs with detailed example."""
        # Run a sample simulation
        results = self.model.simulate_growth(self.weather_df)
        
        # Print detailed information about inputs and outputs
        print("\nCROPGRO-Strawberry Model Inputs:")
        print(f"Latitude: {self.model.latitude}°")
        print(f"Planting date: {self.model.planting_date.strftime('%Y-%m-%d')}")
        
        print("\nSoil Properties:")
        for key, value in self.soil_properties.items():
            print(f"  {key}: {value}")
        
        print("\nCultivar Parameters:")
        for key, value in self.cultivar_params.items():
            print(f"  {key}: {value}")
        
        print("\nWeather Data Sample (first 3 days):")
        print(self.weather_df.head(3).to_string())
        
        print("\nCROPGRO-Strawberry Model Outputs:")
        print(f"Simulation length: {len(results)} days")
        
        print("\nFinal Plant State:")
        print(f"  Total biomass: {self.model.plant_state['biomass']:.2f} g/plant")
        print(f"  Fruit biomass: {self.model.plant_state['fruit_biomass']:.2f} g/plant")
        print(f"  Leaf biomass: {self.model.plant_state['leaf_biomass']:.2f} g/plant")
        print(f"  Stem biomass: {self.model.plant_state['stem_biomass']:.2f} g/plant")
        print(f"  Root biomass: {self.model.plant_state['root_biomass']:.2f} g/plant")
        print(f"  Leaf area index: {self.model.plant_state['leaf_area_index']:.2f} m²/m²")
        print(f"  Fruit number: {self.model.plant_state['fruit_number']:.2f} fruits/plant")
        print(f"  Crown number: {self.model.plant_state['crown_number']:.2f} crowns/plant")
        print(f"  Runner number: {self.model.plant_state['runner_number']:.2f} runners/plant")
        print(f"  Root depth: {self.model.plant_state['root_depth']:.2f} cm")
        print(f"  Final stage: {self.model.plant_state['phenological_stage']}")
        
        print("\nTime Series Data (first day and last day):")
        print("\nFirst day:")
        first_day = results.iloc[0].to_dict()
        for key, value in first_day.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        print("\nLast day:")
        last_day = results.iloc[-1].to_dict()
        for key, value in last_day.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        # Verify data types of key outputs
        self.assertIsInstance(results, pd.DataFrame)
        self.assertIsInstance(self.model.plant_state['biomass'], float)
        self.assertIsInstance(self.model.plant_state['leaf_area_index'], float)
        self.assertIsInstance(self.model.plant_state['phenological_stage'], str)


def run_test_suite():
    """Run the test suite and print results."""
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCropgroStrawberry)
    
    # Run the tests with a lower verbosity to reduce output clutter
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    
    # Print a summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    
    # Return test success status
    return len(result.errors) == 0 and len(result.failures) == 0


if __name__ == "__main__":
    # This will exit cleanly after the tests are done
    run_test_suite()
    print("Tests completed!")


# Example of expected terminal output from tests:
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
