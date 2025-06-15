#!/usr/bin/env python3
"""Run validation for all strawberry experiments automatically."""

import os
import subprocess
import sys
from pathlib import Path

def run_validation(srx_file, output_dir="validation_results"):
    """Run validation for a single experiment file."""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Generate report filename
    experiment_name = Path(srx_file).stem
    report_file = f"{output_dir}/{experiment_name}_validation.txt"
    
    try:
        print(f"\n{'='*60}")
        print(f"Running validation for: {experiment_name}")
        print(f"{'='*60}")
        
        # Run the validation
        result = subprocess.run([
            sys.executable, "validate_models.py", 
            srx_file,
            "--dssat-dir", "dssat-csm-os-develop",
            "--tolerance", "1.0",
            "--report", report_file
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout)
        print(f"✅ PASSED: {experiment_name}")
        print(f"   Report saved to: {report_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {experiment_name}")
        print(f"   Error: {e}")
        if e.stdout:
            print(f"   Output: {e.stdout}")
        if e.stderr:
            print(f"   Error details: {e.stderr}")
        return False

def main():
    """Run validation for all strawberry experiments."""
    # Find all strawberry experiment files
    strawberry_dir = "dssat-csm-data-develop/Strawberry"
    srx_files = list(Path(strawberry_dir).glob("*.SRX"))
    
    if not srx_files:
        print(f"No .SRX files found in {strawberry_dir}")
        return
    
    print(f"Found {len(srx_files)} strawberry experiments to validate:")
    for f in srx_files:
        print(f"  - {f.name}")
    
    # Run validation for each experiment
    results = {}
    for srx_file in srx_files:
        success = run_validation(str(srx_file))
        results[srx_file.stem] = success
    
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(results.values())
    total = len(results)
    
    for experiment, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{experiment:15} : {status}")
    
    print(f"\nOverall: {passed}/{total} experiments passed validation")
    
    if passed == total:
        print("🎉 All validations PASSED! Your Python model is fully validated!")
    else:
        print(f"⚠️  {total - passed} validation(s) failed. Check individual reports.")

if __name__ == "__main__":
    main() 