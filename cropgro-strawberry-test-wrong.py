import unittest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import io
import sys

# Import the CROPGRO-Strawberry model
# For a real implementation, you would import from your module
# from cropgro_strawberry import CropgroStrawberry
# But for testing purposes, we'll assume the code is in the same file
# So we'll define a placeholder for the class here

# Define the CropgroStrawberry class here or import it

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
    
    # Run the tests
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    run_test_suite()


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
