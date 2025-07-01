#!/usr/bin/env python3
"""Simplified test version of compare_with_fortran.py for demonstration."""

import argparse
import os
import subprocess
import sys
from datetime import datetime

def parse_dssat_date(code: str) -> str:
    """Convert DSSAT YYDDD date code to YYYY-MM-DD string."""
    year = 2000 + int(code[:2])
    doy = int(code[2:])
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")

def parse_srx_file(path: str):
    """Extract planting date and weather station from SRX file."""
    print(f"Parsing SRX file: {path}")
    planting_code = None
    wsta = None
    
    with open(path) as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if line.startswith("@L ID_FIELD"):
            if i + 1 < len(lines):
                parts = lines[i + 1].split()
                if len(parts) >= 3:
                    wsta = parts[2]
        if line.startswith("@P PDATE"):
            if i + 1 < len(lines):
                parts = lines[i + 1].split()
                if len(parts) >= 2:
                    planting_code = parts[1]
    
    planting_date = parse_dssat_date(planting_code) if planting_code else None
    print(f"Found planting date: {planting_date}, weather station: {wsta}")
    return planting_date, wsta

def run_dssat(srx_path: str, dssat_dir: str):
    """Run DSSAT using the executable directly."""
    print(f"Running DSSAT for: {srx_path}")
    
    # Use the DSSAT executable directly
    dssat_exe = "/app/dssat/dscsm048"
    if not os.path.exists(dssat_exe):
        dssat_exe = os.path.abspath(os.path.join(dssat_dir, "dscsm048"))
        if not os.path.exists(dssat_exe):
            raise FileNotFoundError(f"DSSAT executable not found at {dssat_exe}")
    
    print(f"Using DSSAT executable: {dssat_exe}")
    
    # Run DSSAT
    result = subprocess.run([dssat_exe, "A", os.path.basename(srx_path)], 
                           cwd=os.path.dirname(srx_path), 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"DSSAT failed with return code: {result.returncode}")
        print(f"STDERR: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args)
    
    print("DSSAT completed successfully!")
    print(f"DSSAT output: {result.stdout}")

def check_output_files(exp_dir: str):
    """Check what output files were generated."""
    print(f"Checking output files in: {exp_dir}")
    
    output_files = [
        "Summary.OUT", "PlantGro.OUT", "FreshWt.OUT", 
        "OVERVIEW.OUT", "Weather.OUT", "Evaluate.OUT"
    ]
    
    found_files = []
    for file in output_files:
        path = os.path.join(exp_dir, file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            found_files.append(f"{file} ({size} bytes)")
    
    print(f"Found output files: {found_files}")
    return len(found_files) > 0

def main():
    parser = argparse.ArgumentParser(description="Test DSSAT comparison")
    parser.add_argument("srx", help="Path to DSSAT .SRX file")
    parser.add_argument("--dssat-dir", default="dssat-csm-os-develop", 
                       help="DSSAT installation directory")
    args = parser.parse_args()

    try:
        print("=== DSSAT Comparison Test ===")
        
        # Step 1: Parse SRX file
        planting_date, wsta = parse_srx_file(args.srx)
        if planting_date is None or wsta is None:
            raise ValueError("Could not parse SRX file")
        
        # Step 2: Run DSSAT
        run_dssat(args.srx, args.dssat_dir)
        
        # Step 3: Check output files
        exp_dir = os.path.dirname(args.srx)
        if check_output_files(exp_dir):
            print("✅ DSSAT run completed successfully!")
            print("✅ Output files generated!")
        else:
            print("❌ No output files found")
            
        print("=== Test Completed ===")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 