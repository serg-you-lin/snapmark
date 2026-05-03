"""
Example 1: Basic Marking

Demonstrates the simplest way to mark DXF files using shortcuts.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


import snapmark as sm

def main():
    folder_1 = "input"
    folder_2 = "input_customizable"
    
    print("=== Example 1A: Mark with filename ===")
    sm.mark_by_name(folder_1, scale_factor=50, min_height=10, max_height=20, 
                    start_y=2, margin=.5, step=2, space=1.5, down_to=3, 
                    mark_color=4, trim_start=0, mark_layer="ENGRAVE", avoid_layers=["Bend, MBend"])
    
    # For files like "PART_123_Q5.dxf", this marks only "PART"
    sm.mark_by_split_text(folder_2, separator='_', part_index=0, scale_factor=50, mark_layer="ENGRAVE")
    
    print("\n✅ Basic marking completed!")

if __name__ == "__main__":
    main()