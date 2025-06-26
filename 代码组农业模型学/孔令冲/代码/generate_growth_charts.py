#!/usr/bin/env python3
"""
Generate comprehensive growth curves and result charts for CROPGRO-Strawberry model.
生成草莓生长的综合曲线图和结果图表。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
import seaborn as sns
import importlib.util
import pathlib

# Import the CropgroStrawberry class
impl_path = (pathlib.Path(__file__).resolve().parent / 
             "cropgro-strawberry-implementation.py")
spec = importlib.util.spec_from_file_location("cropgro_impl", impl_path)
impl_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def create_comprehensive_growth_charts(results_df, save_path='growth_charts.png'):
    """Create comprehensive growth charts and save to file."""
    
    # Create figure with multiple subplots
    fig = plt.figure(figsize=(20, 24))
    
    # 1. Biomass Growth Over Time
    ax1 = plt.subplot(4, 3, 1)
    ax1.plot(results_df['dap'], results_df['biomass'], 'b-', linewidth=2, label='Total Biomass')
    ax1.plot(results_df['dap'], results_df['leaf_biomass'], 'g-', linewidth=2, label='Leaf Biomass')
    ax1.plot(results_df['dap'], results_df['stem_biomass'], 'k-', linewidth=2, label='Stem Biomass')
    ax1.plot(results_df['dap'], results_df['root_biomass'], 'r-', linewidth=2, label='Root Biomass')
    ax1.plot(results_df['dap'], results_df['fruit_biomass'], 'm-', linewidth=2, label='Fruit Biomass')
    ax1.set_xlabel('Days After Planting', fontsize=12)
    ax1.set_ylabel('Biomass (g/plant)', fontsize=12)
    ax1.set_title('Plant Biomass Development', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. Leaf Area Index
    ax2 = plt.subplot(4, 3, 2)
    ax2.plot(results_df['dap'], results_df['leaf_area_index'], 'g-', linewidth=2)
    ax2.set_xlabel('Days After Planting', fontsize=12)
    ax2.set_ylabel('Leaf Area Index (m²/m²)', fontsize=12)
    ax2.set_title('Leaf Area Index Development', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 3. Fruit Development
    ax3 = plt.subplot(4, 3, 3)
    ax3.plot(results_df['dap'], results_df['fruit_number'], 'm-', linewidth=2, label='Fruit Number')
    ax3_twin = ax3.twinx()
    ax3_twin.plot(results_df['dap'], results_df['fruit_biomass'], 'r--', linewidth=2, label='Fruit Biomass')
    ax3.set_xlabel('Days After Planting', fontsize=12)
    ax3.set_ylabel('Fruit Number (per plant)', fontsize=12, color='m')
    ax3_twin.set_ylabel('Fruit Biomass (g/plant)', fontsize=12, color='r')
    ax3.set_title('Fruit Development', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # 4. Crown and Runner Development
    ax4 = plt.subplot(4, 3, 4)
    ax4.plot(results_df['dap'], results_df['crown_number'], 'b-', linewidth=2, label='Crowns')
    ax4.plot(results_df['dap'], results_df['runner_number'], 'r-', linewidth=2, label='Runners')
    ax4.set_xlabel('Days After Planting', fontsize=12)
    ax4.set_ylabel('Number per Plant', fontsize=12)
    ax4.set_title('Crown and Runner Development', fontsize=14, fontweight='bold')
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # 5. Root Depth
    ax5 = plt.subplot(4, 3, 5)
    ax5.plot(results_df['dap'], results_df['root_depth'], 'brown', linewidth=2)
    ax5.set_xlabel('Days After Planting', fontsize=12)
    ax5.set_ylabel('Root Depth (cm)', fontsize=12)
    ax5.set_title('Root Depth Development', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # 6. Water Stress
    ax6 = plt.subplot(4, 3, 6)
    ax6.plot(results_df['dap'], results_df['water_stress'], 'r-', linewidth=2)
    ax6.set_xlabel('Days After Planting', fontsize=12)
    ax6.set_ylabel('Water Stress Factor (0-1)', fontsize=12)
    ax6.set_title('Water Stress Development', fontsize=14, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    
    # 7. Photosynthesis and Transpiration
    ax7 = plt.subplot(4, 3, 7)
    ax7.plot(results_df['dap'], results_df['photosynthesis'], 'g-', linewidth=2, label='Photosynthesis')
    ax7_twin = ax7.twinx()
    ax7_twin.plot(results_df['dap'], results_df['transpiration'], 'b--', linewidth=2, label='Transpiration')
    ax7.set_xlabel('Days After Planting', fontsize=12)
    ax7.set_ylabel('Photosynthesis (g/plant/day)', fontsize=12, color='g')
    ax7_twin.set_ylabel('Transpiration (mm/day)', fontsize=12, color='b')
    ax7.set_title('Photosynthesis and Transpiration', fontsize=14, fontweight='bold')
    ax7.grid(True, alpha=0.3)
    
    # 8. Thermal Time
    ax8 = plt.subplot(4, 3, 8)
    ax8.plot(results_df['dap'], results_df['thermal_time'], 'orange', linewidth=2)
    ax8.set_xlabel('Days After Planting', fontsize=12)
    ax8.set_ylabel('Thermal Time (°C·day)', fontsize=12)
    ax8.set_title('Thermal Time Accumulation', fontsize=14, fontweight='bold')
    ax8.grid(True, alpha=0.3)
    
    # 9. Day Length
    ax9 = plt.subplot(4, 3, 9)
    ax9.plot(results_df['dap'], results_df['daylength'], 'purple', linewidth=2)
    ax9.set_xlabel('Days After Planting', fontsize=12)
    ax9.set_ylabel('Day Length (hours)', fontsize=12)
    ax9.set_title('Day Length Variation', fontsize=14, fontweight='bold')
    ax9.grid(True, alpha=0.3)
    
    # 10. Phenological Development
    ax10 = plt.subplot(4, 3, 10)
    stages = list(set(results_df['stage']))
    stage_values = [stages.index(stage) for stage in results_df['stage']]
    ax10.plot(results_df['dap'], stage_values, 'b-', linewidth=2)
    ax10.set_xlabel('Days After Planting', fontsize=12)
    ax10.set_ylabel('Development Stage', fontsize=12)
    ax10.set_title('Phenological Development', fontsize=14, fontweight='bold')
    ax10.set_yticks(range(len(stages)))
    ax10.set_yticklabels(stages, rotation=45, ha='right')
    ax10.grid(True, alpha=0.3)
    
    # 11. Biomass Partitioning (Pie chart for final state)
    ax11 = plt.subplot(4, 3, 11)
    final_biomass = results_df.iloc[-1]
    biomass_parts = [final_biomass['leaf_biomass'], final_biomass['stem_biomass'], 
                    final_biomass['root_biomass'], final_biomass['fruit_biomass']]
    labels = ['Leaf', 'Stem', 'Root', 'Fruit']
    colors = ['green', 'brown', 'orange', 'red']
    ax11.pie(biomass_parts, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax11.set_title('Final Biomass Partitioning', fontsize=14, fontweight='bold')
    
    # 12. Growth Rate Analysis
    ax12 = plt.subplot(4, 3, 12)
    # Calculate daily growth rate
    daily_growth = results_df['biomass'].diff()
    ax12.plot(results_df['dap'][1:], daily_growth[1:], 'g-', linewidth=2)
    ax12.set_xlabel('Days After Planting', fontsize=12)
    ax12.set_ylabel('Daily Growth Rate (g/plant/day)', fontsize=12)
    ax12.set_title('Daily Biomass Growth Rate', fontsize=14, fontweight='bold')
    ax12.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Comprehensive growth charts saved to: {save_path}")
    return fig

def create_summary_statistics_chart(results_df, save_path='summary_statistics.png'):
    """Create summary statistics chart."""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Final values summary
    final_values = results_df.iloc[-1]
    summary_data = {
        'Total Biomass': final_values['biomass'],
        'Fruit Biomass': final_values['fruit_biomass'],
        'Leaf Biomass': final_values['leaf_biomass'],
        'Stem Biomass': final_values['stem_biomass'],
        'Root Biomass': final_values['root_biomass']
    }
    
    ax1.bar(summary_data.keys(), summary_data.values(), color=['blue', 'red', 'green', 'brown', 'orange'])
    ax1.set_title('Final Biomass Distribution', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Biomass (g/plant)', fontsize=12)
    ax1.tick_params(axis='x', rotation=45)
    
    # Growth metrics
    growth_metrics = {
        'Max LAI': results_df['leaf_area_index'].max(),
        'Final LAI': final_values['leaf_area_index'],
        'Fruit Number': final_values['fruit_number'],
        'Crown Number': final_values['crown_number'],
        'Root Depth': final_values['root_depth']
    }
    
    ax2.bar(growth_metrics.keys(), growth_metrics.values(), color=['lightgreen', 'green', 'red', 'blue', 'orange'])
    ax2.set_title('Growth Metrics', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Value', fontsize=12)
    ax2.tick_params(axis='x', rotation=45)
    
    # Time series of key variables
    ax3.plot(results_df['dap'], results_df['biomass'], 'b-', label='Total Biomass', linewidth=2)
    ax3.plot(results_df['dap'], results_df['leaf_area_index'] * 100, 'g-', label='LAI × 100', linewidth=2)
    ax3.set_xlabel('Days After Planting', fontsize=12)
    ax3.set_ylabel('Value', fontsize=12)
    ax3.set_title('Key Growth Variables Over Time', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Phenological stage distribution
    stage_counts = results_df['stage'].value_counts()
    ax4.pie(stage_counts.values, labels=stage_counts.index, autopct='%1.1f%%', startangle=90)
    ax4.set_title('Time Spent in Each Growth Stage', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Summary statistics chart saved to: {save_path}")
    return fig

def run_simulation_and_generate_charts():
    """Run simulation and generate all charts."""
    
    # Define parameters
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
    
    # Create weather data (using real data if available)
    try:
        # Try to use real weather data
        from show_dataframe_details import read_wth_file
        wth_path = "dssat-csm-data-develop/Weather/UFBA1401.WTH"
        weather_df = read_wth_file(wth_path)
        planting_date = "2014-10-09"  # From UFBA1401.SRX
        print(f"Using real weather data from {wth_path}")

        # 自动标准化天气数据列名，适配Python模型
        weather_df = weather_df.rename(columns={
            "TMAX": "tmax",
            "TMIN": "tmin",
            "SRAD": "solar_radiation",
            "RAIN": "rainfall",
            "RHUM": "rh",
            "WIND": "wind_speed",
            "DATE": "date"
        })
        # 自动确保日期列为'%Y-%m-%d'字符串格式
        if "date" in weather_df.columns:
            # 如果是5位数字（YYDDD），用parse_dssat_date转换
            if weather_df["date"].astype(str).str.match(r"^\d{5}$").all():
                from show_dataframe_details import parse_dssat_date
                weather_df["date"] = weather_df["date"].apply(parse_dssat_date)
            else:
                weather_df["date"] = weather_df["date"].astype(str)
    except:
        # Fallback to synthetic data
        print("Using synthetic weather data")
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
        planting_date = start_date
    
    # Initialize and run model
    model = CropgroStrawberry(
        latitude=40.0,
        planting_date=planting_date,
        soil_properties=soil_properties,
        cultivar_params=cultivar_params
    )
    
    results = model.simulate_growth(weather_df)
    
    # Generate charts
    print("Generating comprehensive growth charts...")
    fig1 = create_comprehensive_growth_charts(results, 'comprehensive_growth_charts.png')
    
    print("Generating summary statistics chart...")
    fig2 = create_summary_statistics_chart(results, 'summary_statistics.png')
    
    # Print summary
    print("\n=== SIMULATION SUMMARY ===")
    print(f"Simulation period: {len(results)} days")
    print(f"Final total biomass: {results['biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final fruit biomass: {results['fruit_biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final leaf area index: {results['leaf_area_index'].iloc[-1]:.3f} m²/m²")
    print(f"Final fruit number: {results['fruit_number'].iloc[-1]:.1f} fruits/plant")
    print(f"Final crown number: {results['crown_number'].iloc[-1]:.1f} crowns/plant")
    print(f"Final root depth: {results['root_depth'].iloc[-1]:.1f} cm")
    print(f"Final phenological stage: {results['stage'].iloc[-1]}")
    
    return model, results, fig1, fig2

if __name__ == "__main__":
    model, results, fig1, fig2 = run_simulation_and_generate_charts()
    print("\nCharts generated successfully!")
    print("Files created:")
    print("- comprehensive_growth_charts.png")
    print("- summary_statistics.png") 