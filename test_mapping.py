#!/usr/bin/env python3
"""Test script to verify column mapping and comparison functionality."""

import sys
import os
sys.path.append('/data')

def test_comparison_with_mapping():
    print("=== Testing Comparison with Column Mapping ===")
    
    try:
        from compare_with_fortran import (
            parse_srx_file, read_wth_file, run_python_model, 
            read_fortran_output, map_python_to_dssat_columns
        )
        
        # Step 1: Parse SRX and read weather data
        srx_path = 'dssat-csm-data-develop/Strawberry/UFBA1401.SRX'
        planting_date, wsta = parse_srx_file(srx_path)
        print(f"✅ Parsed: planting_date={planting_date}, wsta={wsta}")
        
        year = planting_date[:4]
        weather_dir = os.path.join('dssat-csm-data-develop', 'Weather')
        matches = [f for f in os.listdir(weather_dir) if f.startswith(f'{wsta}{year[2:]}') and f.endswith('.WTH')]
        wth_path = os.path.join(weather_dir, matches[0])
        wth_df = read_wth_file(wth_path)
        print(f"✅ Weather data loaded: {wth_df.shape}")
        
        # Step 2: Run Python model
        print("🔄 Running Python model...")
        py_df = run_python_model(wth_df, planting_date)
        print(f"✅ Python model completed: {py_df.shape}")
        print(f"Python columns: {list(py_df.columns)}")
        
        # Step 3: Map Python columns to DSSAT format
        py_df_mapped = map_python_to_dssat_columns(py_df)
        print(f"✅ Column mapping completed")
        print(f"Mapped columns: {list(py_df_mapped.columns)}")
        
        # Step 4: Read DSSAT output
        exp_dir = 'dssat-csm-data-develop/Strawberry'
        fort_df = read_fortran_output(exp_dir)
        print(f"✅ DSSAT output loaded: {fort_df.shape}")
        print(f"DSSAT columns: {list(fort_df.columns)}")
        
        # Step 5: Find common columns
        common_cols = [c for c in fort_df.columns if c in py_df_mapped.columns]
        print(f"✅ Common columns found: {common_cols}")
        
        if common_cols:
            # Step 6: Compare data
            min_len = min(len(fort_df), len(py_df_mapped))
            fort_subset = fort_df[common_cols].head(min_len)
            py_subset = py_df_mapped[common_cols].head(min_len)
            
            print(f"\n📊 Comparison Results ({min_len} rows, {len(common_cols)} columns):")
            print("\nFirst 3 rows of DSSAT data:")
            print(fort_subset.head(3))
            print("\nFirst 3 rows of Python data:")
            print(py_subset.head(3))
            
            # Calculate differences
            print("\n📈 Column-wise Analysis:")
            for col in common_cols:
                try:
                    dssat_vals = fort_subset[col].values
                    python_vals = py_subset[col].values
                    
                    dssat_mean = dssat_vals.mean() if len(dssat_vals) > 0 else 0
                    python_mean = python_vals.mean() if len(python_vals) > 0 else 0
                    diff_pct = abs(dssat_mean - python_mean) / max(abs(dssat_mean), 1e-10) * 100
                    
                    print(f"  {col:6s}: DSSAT={dssat_mean:8.3f}, Python={python_mean:8.3f}, Diff={diff_pct:6.1f}%")
                except Exception as e:
                    print(f"  {col:6s}: Error calculating - {e}")
                    
            print("\n✅ Comparison completed successfully!")
        else:
            print("❌ No common columns found for comparison")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comparison_with_mapping() 