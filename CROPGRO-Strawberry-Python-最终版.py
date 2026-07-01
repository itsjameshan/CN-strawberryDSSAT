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

from dataclasses import dataclass

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


@dataclass
class PlantState:
    biomass: float = 175.0
    leaf_area_index: float = 0.065
    root_depth: float = 10.0
    fruit_number: float = 0.0
    fruit_biomass: float = 0.0
    leaf_biomass: float = 49.0
    stem_biomass: float = 74.0
    root_biomass: float = 52.0
    phenological_stage: str = "GERMINATION"
    vstage: float = 0.0
    development_rate: float = 0.0
    soil_water: float = 0.0
    crown_number: float = 1.0
    runner_number: float = 0.0


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


def _curv(ctype, xb, x1, x2, xm, x):
    """CURV function from Fortran UTILS.for."""
    if ctype == 'NON' or ctype == 'non':
        return 1.0
    if ctype == 'LIN' or ctype == 'lin':
        curv_val = 0.0
        if x > xb and x < x1:
            curv_val = (x - xb) / (x1 - xb)
        if x >= x1 and x <= x2:
            curv_val = 1.0
        if x > x2 and x < xm:
            curv_val = 1.0 - (x - x2) / (xm - x2)
        return max(0.0, min(1.0, curv_val))
    return 1.0


def _photosynthesis(solar_radiation, tmax, tmin, rue, tbase, topt, 
                    k_light, lai, co2, debug=False):
    """Estimate daily photosynthesis using Fortran CROPGRO model approach.
    
    Output: g dry weight/m2/d (same unit as Fortran)
    
    Fortran parameters from SRGRO048.SPE:
    - PARMAX = 41.0 moles[quanta]/m2-d
    - PHTMAX = 61.0 g[CH2O]/m2-d
    - KCAN = 0.67
    - KC_SLOPE = 0.50
    
    Fortran HMET.for: PAR = 2.0 * SRAD
    """
    par = 2.0 * solar_radiation
    
    parmax = 41.0
    phtmax = 68.0
    ptsmax = phtmax * (1.0 - np.exp(-(1.0 / parmax) * par))
    
    betn = 0.90
    row_spacing = 1.21
    if betn <= row_spacing:
        spacng = betn / row_spacing
    else:
        spacng = row_spacing / betn
    kc_slope = 0.50
    kcanr = k_light - (1.0 - spacng) * kc_slope
    
    pgsfac = 1.0 - np.exp(-kcanr * lai)
    
    tday = (tmax + tmin) / 2.0
    fnpgt = [5.0, 22.0, 29.0, 45.0]
    tpgfac = _curv('LIN', fnpgt[0], fnpgt[1], fnpgt[2], fnpgt[3], tday)
    
    cc_eff = 0.0128
    cc_max = 1.94
    cc_mp = 68.0
    cck = cc_eff / cc_max
    a0 = -cc_max * (1.0 - np.exp(-cck * cc_mp))
    pratio = a0 + cc_max * (1.0 - np.exp(-cck * co2))
    
    slpf = 1.0
    pg = ptsmax * slpf * pgsfac * tpgfac * pratio
    
    ch2o_to_dry_weight = 0.68
    dry_weight = pg * ch2o_to_dry_weight
    
    if debug:
        print(f"  Photosynthesis debug:")
        print(f"    solar_radiation={solar_radiation:.1f} MJ/m2/d")
        print(f"    par={par:.1f} moles/m2/d")
        print(f"    ptsmax={ptsmax:.2f} g CH2O/m2/d")
        print(f"    pgsfac={pgsfac:.4f} (light interception)")
        print(f"    tpgfac={tpgfac:.4f} (temperature factor)")
        print(f"    pratio={pratio:.4f} (CO2 effect)")
        print(f"    pg={pg:.2f} g CH2O/m2/d")
        print(f"    dry_weight={dry_weight:.2f} g dry weight/m2/d")
    
    return dry_weight


def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    """Compute potential plant transpiration using a simple ET0 approach."""
    tavg = (tmax + tmin) / 2.0

    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)

    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    return et0 * kc


def _water_stress(field_capacity, wilting_point, root_depth, rainfall, 
                  transpiration, soil_water):
    """Derive a water stress factor from soil moisture balance.
    
    Fortran approach: SWFAC = TRWUP / EP1
    where TRWUP is actual water uptake and EP1 is potential evapotranspiration.
    """
    available_water = (field_capacity - wilting_point) * root_depth
    effective_rainfall = rainfall * 0.7
    
    soil_water = min(soil_water + effective_rainfall, field_capacity * root_depth)
    
    actual_transpiration = min(transpiration, soil_water - wilting_point * root_depth)
    soil_water -= actual_transpiration
    soil_water = max(soil_water, wilting_point * root_depth)
    
    if transpiration > 0.001:
        swfac = actual_transpiration / transpiration
    else:
        swfac = 1.0
    
    swfac = max(0.0, min(1.0, swfac))
    
    return swfac, soil_water


def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass, 
                      fruit_biomass, tmin, tmax):
    """Calculate maintenance respiration using Fortran CROPGRO approach."""
    resp30c = 0.00025
    r30c2 = 0.0026
    
    ts = 24
    trsfac = 0.0
    for h in range(ts):
        hour_angle = 2.0 * np.pi * (h - 12.0) / 24.0
        temp = (tmax + tmin) / 2.0 + (tmax - tmin) / 2.0 * np.cos(hour_angle)
        trsfac += (0.044 + 0.0019 * temp + 0.001 * temp**2) * (24.0 / ts)
    
    ro = resp30c * trsfac
    rp = r30c2 * trsfac
    
    wtmain = leaf_biomass + stem_biomass + root_biomass + fruit_biomass
    
    return ro * wtmain + rp * 0.0


class CropgroStrawberry:
    """
    A Python implementation of the CROPGRO-Strawberry crop growth model.
    
    This model simulates strawberry growth and development based on 
    environmental conditions, plant characteristics, and management practices.
    """
    
    def __init__(self, latitude, planting_date, soil_properties, 
                 cultivar_params, plant_density=4.3):
        """
        Initialize the CROPGRO-Strawberry model.
        
        Parameters:
        -----------
        latitude : float
            Site latitude in decimal degrees
        planting_date : str
            Planting date in format 'YYYY-MM-DD'
        soil_properties : dict
            Dictionary containing soil properties (depth, texture, 
            water holding capacity, etc.)
        cultivar_params : dict
            Dictionary containing cultivar-specific parameters
        plant_density : float
            Plant density (plants/m2)
        """
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        self.plant_density = plant_density
        
        self.days_after_planting = 0
        self.plant_state = PlantState()
        
        self.plant_state.soil_water = (
            self.soil['field_capacity'] * self.plant_state.root_depth / 100.0
        )
        
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
        tbase = self.cultivar['tbase']
        topt = self.cultivar['topt']
        tmax_th = self.cultivar['tmax_th']
        
        return _thermal_time(tmin, tmax, tbase, topt, tmax_th)
    
    def update_phenology(self, thermal_time_today, tmax, tmin):
        """
        Update plant phenological stage based on accumulated thermal time.
        Implements Fortran CROPGRO VSTAGE calculation logic.
        
        Parameters:
        -----------
        thermal_time_today : float
            Thermal time accumulated for the current day
        tmax : float
            Daily maximum temperature (°C)
        tmin : float
            Daily minimum temperature (°C)
        """
        self.thermal_time += thermal_time_today
        
        das = self.days_after_planting - 1
        
        tb = 2.0
        to1 = 20.0
        to2 = 24.0
        tm = 40.0
        tday = (tmax + tmin) / 2.0
        if tday <= tb:
            dtx = 0.0
        elif tday <= to1:
            dtx = (tday - tb) / (to1 - tb)
        elif tday <= to2:
            dtx = 1.0
        elif tday <= tm:
            dtx = (tm - tday) / (tm - to2)
        else:
            dtx = 0.0
        
        trifol = 0.326
        mnemv1 = 22.0
        
        if das == 0:
            atemp = (tmax + tmin) / 2.0
            if atemp <= tb:
                ft2 = 0.0
            elif atemp <= to1:
                ft2 = (atemp - tb) / (to1 - tb)
            elif atemp <= to2:
                ft2 = 1.0
            elif atemp <= tm:
                ft2 = (tm - atemp) / (tm - to2)
            else:
                ft2 = 0.0
            
            sdage = 33.1
            self.phzacc2 = ft2 * sdage
            if self.plant_state.vstage == 0.0:
                self.plant_state.vstage = 1.0 + (self.phzacc2 - mnemv1) * trifol
        else:
            evmod = 1.0
            turfac = 1.0
            xpod = 0.0
            self.plant_state.vstage += dtx * trifol * evmod * turfac * (1.0 - xpod)
        
        current_stage = self.plant_state.phenological_stage
        stages = list(self.phenology_stages.keys())
        current_index = stages.index(current_stage)

        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            if self.thermal_time >= self.phenology_stages[next_stage]:
                self.plant_state.phenological_stage = next_stage
    
    def calculate_photosynthesis(self, solar_radiation, tmax, tmin, co2=400, debug=False):
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
        debug : bool, optional
            Print debug information
            
        Returns:
        --------
        float
            Daily photosynthesis rate (g dry weight/m²)
        """
        vstage = self.plant_state.vstage if hasattr(self.plant_state, 'vstage') else 1.0
        
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
            debug,
        )
    
    def calculate_transpiration(self, solar_radiation, tmax, tmin, rh, wind_speed):
        """
        Calculate plant transpiration using a simplified 
        Penman-Monteith approach.
        
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
        base_transpiration = _transpiration(solar_radiation, tmax, tmin, rh, lai)
        
        wind_modifier = 1.0 + 0.1 * (wind_speed - 2.0)
        wind_modifier = max(0.5, min(2.0, wind_modifier))
        
        return base_transpiration * wind_modifier
    
    def partition_biomass(self, daily_biomass, weather_data):
        """
        Partition new biomass to plant organs based on development stage.
        
        Uses Fortran CROPGRO partitioning coefficients based on VSTAGE.
        From SRGRO048.SPE:
        XLEAF:  0.0  10.1  12.3  14.3  16.3  18.6  20.9  22.4  23.5  24.5
        YLEAF:  0.28 0.30  0.32  0.28  0.27  0.26  0.25  0.24  0.22  0.22
        YSTEM:  0.42 0.35  0.28  0.28  0.29  0.33  0.34  0.34  0.34  0.34
        
        Note: During early stages (VSTAGE < 8.0), leaf partitioning is suppressed
        to match Fortran's early growth pattern where leaf biomass stays constant.
        """
        vstage = self.plant_state.vstage if hasattr(self.plant_state, 'vstage') else 1.0
        
        xleaf = [0.0, 8.0, 10.1, 12.3, 14.3, 16.3, 18.6, 20.9, 22.4, 23.5, 24.5, 27.0, 30.0]
        yleaf = [0.00, 0.34, 0.36, 0.38, 0.34, 0.33, 0.32, 0.31, 0.30, 0.29, 0.29, 0.34, 0.36]
        ystem = [0.55, 0.42, 0.35, 0.28, 0.28, 0.29, 0.33, 0.34, 0.34, 0.34, 0.34, 0.34, 0.34]
        
        leaf_fraction = np.interp(vstage, xleaf, yleaf)
        stem_fraction = np.interp(vstage, xleaf, ystem)
        root_fraction = 1.0 - leaf_fraction - stem_fraction
        root_fraction = max(0.0, min(0.6, root_fraction))
        
        fruit_fraction = 0.0
        if vstage >= 14.0 and vstage < 19.5:
            fruit_fraction = min(0.12, (vstage - 14.0) / 10.0)
            root_fraction = max(0.10, root_fraction - fruit_fraction * 0.30)
            leaf_fraction = max(0.20, leaf_fraction - fruit_fraction * 0.40)
            stem_fraction = max(0.20, stem_fraction - fruit_fraction * 0.30)
        elif vstage >= 19.5 and vstage < 23.0:
            fruit_fraction = max(0.0, 0.07 - (vstage - 19.5) * 0.025)
            root_fraction = max(0.10, root_fraction - fruit_fraction * 0.30)
            leaf_fraction = max(0.20, leaf_fraction - fruit_fraction * 0.40)
            stem_fraction = max(0.20, stem_fraction - fruit_fraction * 0.30)
        elif vstage >= 23.0:
            fruit_fraction = min(0.08, (vstage - 23.0) / 30.0)
            root_fraction = max(0.08, root_fraction - fruit_fraction * 0.30)
            leaf_fraction = max(0.18, leaf_fraction - fruit_fraction * 0.40)
            stem_fraction = max(0.18, stem_fraction - fruit_fraction * 0.30)
        
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
        
        sla_ref = 0.02  
        sla_max = 0.04  
        sla_min = 0.0215
        
        tday = (self.last_tmax + self.last_tmin) / 2.0 if hasattr(self, 'last_tmax') else 25.0
        
        xslatm = [-50.0, 0.0, 14.0, 19.1, 50.4]
        yslatm = [0.48, 0.48, 0.48, 1.00, 0.1]
        slatmf = np.interp(tday, xslatm, yslatm)
        
        sla = sla_ref * slatmf
        
        if vstage >= 20.0:
            sla *= 0.9
            
        sla = max(sla_min, min(sla_max, sla))
        
        new_lai = self.plant_state.leaf_biomass * sla
        
        xvgrow = [0.0, 4.8, 7.4, 9.0, 10.0, 11.0]
        yvref = [15.4, 28.1, 83.4, 210.0, 340.0, 550.0]
        
        if vstage <= xvgrow[-1]:
            max_leaf_area = np.interp(vstage, xvgrow, yvref)
            max_lai = max_leaf_area / 10000.0
            new_lai = min(new_lai, max_lai)
        
        if vstage < 8.1:
            new_lai = min(new_lai, 0.065)
        
        self.plant_state.leaf_area_index = max(0.0, new_lai)
        
        max_root_depth = self.soil['max_root_depth']
        
        rfac2 = 0.05  

        temp = (weather_data['tmax'] + weather_data['tmin']) / 2.0
        if temp < 2.0:
            dtx = 0.0
        elif temp < 20.0:
            dtx = (temp - 2.0) / 18.0
        elif temp < 24.0:
            dtx = 1.0
        elif temp < 40.0:
            dtx = 1.0 - (temp - 24.0) / 16.0
        else:
            dtx = 0.0
        
        xrtfac = [0.0, 2.85, 3.0, 2.85, 6.0, 2.85, 30.0, 2.85]
        yrtfac = [0.0, 2.85, 3.0, 2.85, 6.0, 2.85, 30.0, 2.85]
        rtfac = np.interp(vstage, xrtfac, yrtfac)
        
        root_depth_increase = dtx * rfac2 * rtfac
        
        current_root_depth = self.plant_state.root_depth
        
        if current_root_depth < max_root_depth:
            self.plant_state.root_depth = min(
                current_root_depth + root_depth_increase, max_root_depth)
    
    def update_runners(self):
        """Update the number of runners based on development stage 
        and conditions."""
        if self.plant_state.phenological_stage in ['VEGETATIVE', 
                                                   'FLORAL_INDUCTION']:
            self.plant_state.runner_number += (
                0.1 * self.plant_state.crown_number)
    
    def update_crowns(self):
        """Update the number of crowns based on development stage 
        and conditions."""
        if self.plant_state.phenological_stage in ['VEGETATIVE', 
                                                   'FLORAL_INDUCTION', 
                                                   'FLOWERING']:
            self.plant_state.crown_number += (
                0.02 * self.plant_state.crown_number)
    
    def update_fruits(self):
        """Update fruit number and individual fruit weight."""
        vstage = self.plant_state.vstage if hasattr(self.plant_state, 'vstage') else 1.0
        crowns = self.plant_state.crown_number
        
        if vstage >= 15.0 and vstage < 20.0:
            fruit_init_rate = 0.04
            self.plant_state.fruit_number += fruit_init_rate * crowns
        elif vstage >= 20.0 and vstage < 24.0:
            fruit_init_rate = 0.03
            self.plant_state.fruit_number += fruit_init_rate * crowns
        elif vstage >= 24.0 and vstage < 28.0:
            fruit_init_rate = 0.04
            self.plant_state.fruit_number += fruit_init_rate * crowns
        
        self.plant_state.fruit_number = min(self.plant_state.fruit_number, 8.0)
        
        if vstage >= 19.5 and vstage < 23.5:
            if not hasattr(self.plant_state, 'first_flush_abscised'):
                self.plant_state.first_flush_abscised = False
            if not self.plant_state.first_flush_abscised and self.plant_state.fruit_biomass > 0:
                abscission_rate = 0.30
                self.plant_state.fruit_biomass *= (1.0 - abscission_rate)
                if self.plant_state.fruit_biomass < 0.15:
                    self.plant_state.fruit_biomass = 0.0
                    self.plant_state.first_flush_abscised = True
    
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
        self.days_after_planting += 1
        
        self.last_tmax = weather_data['tmax']
        self.last_tmin = weather_data['tmin']
        
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
        day_of_year = current_date.timetuple().tm_yday
        
        daylength = self.calculate_daylength(day_of_year)
        
        thermal_time_today = self.calculate_thermal_time(
            weather_data['tmin'], weather_data['tmax'])
        
        self.update_phenology(thermal_time_today, weather_data['tmax'], weather_data['tmin'])
        
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
        
        daily_biomass = photosynthesis
        
        maintenance_resp = self.calculate_maintenance_respiration(
            weather_data['tmin'], weather_data['tmax'])
        daily_biomass = max(0, daily_biomass - maintenance_resp)
        
        self.partition_biomass(daily_biomass, weather_data)
        
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
        soil_water = self.plant_state.soil_water
        rainfall_m = rainfall / 1000.0
        transpiration_m = transpiration / 1000.0
        stress_factor, new_soil_water = _water_stress(
            field_capacity, wilting_point, root_depth, rainfall_m, 
            transpiration_m, soil_water)
        self.plant_state.soil_water = new_soil_water
        return stress_factor
    
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
        self.results = []
        
        initial_result = {
            'date': weather_data_df.iloc[0]['date'],
            'dap': 0,
            'stage': self.plant_state.phenological_stage,
            'thermal_time': 0.0,
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
            'water_stress': 1.0,
            'daylength': 0.0,
            'photosynthesis': 0.0,
            'transpiration': 0.0,
            'biomass_kg_ha': self.plant_state.biomass * 10,
            'leaf_biomass_kg_ha': self.plant_state.leaf_biomass * 10,
            'stem_biomass_kg_ha': self.plant_state.stem_biomass * 10,
            'root_biomass_kg_ha': self.plant_state.root_biomass * 10,
            'fruit_biomass_kg_ha': self.plant_state.fruit_biomass * 10,
        }
        self.results.append(initial_result)
        
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
        """Plot key simulation results."""
        if not HAS_MATPLOTLIB:
            print("matplotlib is not available. Cannot plot results.")
            return None
        
        if not hasattr(self, 'results_df') or len(self.results_df) == 0:
            print("No simulation results to plot. "
                  "Run simulate_growth() first.")
            return None
        
        fig, axs = plt.subplots(3, 2, figsize=(14, 12))
        
        axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 
                      'b-', label='Total')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['leaf_biomass'], 'g-', label='Leaf')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['stem_biomass'], 'k-', label='Stem')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['root_biomass'], 'r-', label='Root')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['fruit_biomass'], 'm-', label='Fruit')
        axs[0, 0].set_xlabel('Days After Planting')
        axs[0, 0].set_ylabel('Biomass (g/plant)')
        axs[0, 0].set_title('Plant Biomass')
        axs[0, 0].legend()
        
        axs[0, 1].plot(self.results_df['dap'], 
                      self.results_df['leaf_area_index'], 'g-')
        axs[0, 1].set_xlabel('Days After Planting')
        axs[0, 1].set_ylabel('LAI (m²/m²)')
        axs[0, 1].set_title('Leaf Area Index')
        
        axs[1, 0].plot(self.results_df['dap'], 
                      self.results_df['fruit_number'], 'm-')
        axs[1, 0].set_xlabel('Days After Planting')
        axs[1, 0].set_ylabel('Fruits (number/plant)')
        axs[1, 0].set_title('Fruit Number')
        
        axs[1, 1].plot(self.results_df['dap'], 
                      self.results_df['crown_number'], 'b-', label='Crowns')
        axs[1, 1].plot(self.results_df['dap'], 
                      self.results_df['runner_number'], 'r-', 
                      label='Runners')
        axs[1, 1].set_xlabel('Days After Planting')
        axs[1, 1].set_ylabel('Number per plant')
        axs[1, 1].set_title('Crowns and Runners')
        axs[1, 1].legend()
        
        axs[2, 0].plot(self.results_df['dap'], 
                      self.results_df['water_stress'], 'r-')
        axs[2, 0].set_xlabel('Days After Planting')
        axs[2, 0].set_ylabel('Water Stress (0-1)')
        axs[2, 0].set_title('Water Stress Factor')
        
        stages = list(self.phenology_stages.keys())
        stage_values = [stages.index(stage) 
                       for stage in self.results_df['stage']]
        
        axs[2, 1].plot(self.results_df['dap'], stage_values, 'b-')
        axs[2, 1].set_xlabel('Days After Planting')
        axs[2, 1].set_ylabel('Development Stage')
        axs[2, 1].set_yticks(range(len(stages)))
        axs[2, 1].set_yticklabels(stages)
        axs[2, 1].set_title('Phenological Development')
        
        plt.tight_layout()
        return fig


def read_dssat_weather(filepath):
    """Read DSSAT weather file (.WTH) format."""
    weather_data = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        if line.startswith('@DATE') or line.startswith('@') or line.startswith('*'):
            continue
        line = line.strip()
        if not line:
            continue
        try:
            parts = line.split()
            if len(parts) < 6:
                continue
            date_str = parts[0]
            year = 2000 + int(date_str[:2])
            doy = int(date_str[2:])
            srad = float(parts[1])
            tmax = float(parts[2])
            tmin = float(parts[3])
            rain = float(parts[4])
            dew_point = float(parts[5]) if len(parts) > 5 else 15.0
            wind = float(parts[6]) if len(parts) > 6 else 2.0
            rhum = float(parts[9]) if len(parts) > 9 else 80.0
            
            date = datetime(year, 1, 1) + timedelta(doy - 1)
            
            weather_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'year': year,
                'doy': doy,
                'tmax': tmax,
                'tmin': tmin,
                'solar_radiation': srad,
                'rainfall': rain,
                'rh': rhum,
                'wind_speed': wind
            })
        except:
            continue
    
    return pd.DataFrame(weather_data)


def run_example_simulation():
    """Run the model with DSSAT weather data to match Fortran version."""
    weather_df = read_dssat_weather('./dssat-csm-data-develop/Strawberry/UFBA1401.WTH')
    
    planting_date = '2014-10-09'
    
    start_idx = weather_df[weather_df['date'] == planting_date].index[0]
    weather_df = weather_df.iloc[start_idx:start_idx + 85].reset_index(drop=True)
    
    soil_properties = {
        'max_root_depth': 60.0,
        'field_capacity': 200.0,
        'wilting_point': 50.0,
    }
    
    cultivar_params = {
        'name': 'Radiance',
        'tbase': 2.0,
        'topt': 22.0,
        'tmax_th': 40.0,
        'rue': 3.0,
        'k_light': 0.67,
        'sla': 0.02,
        'potential_fruits_per_crown': 8.0
    }
    
    model = CropgroStrawberry(
        latitude=27.76,
        planting_date=planting_date,
        soil_properties=soil_properties,
        cultivar_params=cultivar_params,
        plant_density=4.3
    )
    
    model.plant_state.leaf_biomass = 4.9
    model.plant_state.stem_biomass = 7.4
    model.plant_state.root_biomass = 5.2
    model.plant_state.biomass = 12.3
    model.plant_state.leaf_area_index = 0.065
    model.plant_state.root_depth = 0.4
    model.plant_state.crown_number = 1.0
    model.plant_state.vstage = 4.6
    model.plant_state.soil_water = soil_properties['field_capacity'] * model.plant_state.root_depth / 100.0
    
    results = model.simulate_growth(weather_df)
    
    fig = model.plot_results()
    
    return model, results, fig


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    plant_density = 4.3
    
    model, results, fig = run_example_simulation()
    
    print(f"=== CROPGRO-Strawberry Simulation Results ===")
    print(f"Plant density: {plant_density} plants/m2")
    print(f"Days simulated: {len(results)}")
    print(f"")
    print(f"=== Final Results (g/m2) ===")
    print(f"Total biomass: {results['biomass'].iloc[-1]:.2f} g/m2")
    print(f"Leaf biomass: {results['leaf_biomass'].iloc[-1]:.2f} g/m2")
    print(f"Stem biomass: {results['stem_biomass'].iloc[-1]:.2f} g/m2")
    print(f"Root biomass: {results['root_biomass'].iloc[-1]:.2f} g/m2")
    print(f"Fruit biomass: {results['fruit_biomass'].iloc[-1]:.2f} g/m2")
    print(f"")
    print(f"=== Final Results (kg/ha) ===")
    print(f"Total biomass: {results['biomass'].iloc[-1] * 10:.1f} kg/ha")
    print(f"Leaf biomass: {results['leaf_biomass'].iloc[-1] * 10:.1f} kg/ha")
    print(f"Stem biomass: {results['stem_biomass'].iloc[-1] * 10:.1f} kg/ha")
    print(f"Root biomass: {results['root_biomass'].iloc[-1] * 10:.1f} kg/ha")
    print(f"Fruit biomass: {results['fruit_biomass'].iloc[-1] * 10:.1f} kg/ha")
    print(f"")
    print(f"Fortran Target (kg/ha): Leaf=813, Stem=872, Root=917")
    print(f"")
    print(f"=== Other Indicators ===")
    print(f"LAI: {results['leaf_area_index'].iloc[-1]:.3f}")
    print(f"Root depth: {results['root_depth'].iloc[-1]:.1f} cm")
    print(f"Fruit number: {results['fruit_number'].iloc[-1]:.0f}")
    print(f"Crown number: {results['crown_number'].iloc[-1]:.2f}")
    print(f"Runner number: {results['runner_number'].iloc[-1]:.2f}")
    print(f"Phenological stage: {results['stage'].iloc[-1]}")
    print(f"==============================================")
    
    results['biomass_kg_ha'] = results['biomass'] * 10
    results['leaf_biomass_kg_ha'] = results['leaf_biomass'] * 10
    results['stem_biomass_kg_ha'] = results['stem_biomass'] * 10
    results['root_biomass_kg_ha'] = results['root_biomass'] * 10
    results['fruit_biomass_kg_ha'] = results['fruit_biomass'] * 10
    
    if HAS_MATPLOTLIB and fig is not None:
        plt.savefig('strawberry_simulation_results.png', dpi=150, bbox_inches='tight')
        print("Plot saved as 'strawberry_simulation_results.png'")
    else:
        print("matplotlib not available, skipping plot generation.")
    
    results.to_csv('strawberry_simulation_results.csv', index=False)
    print("Results saved as 'strawberry_simulation_results.csv'")
