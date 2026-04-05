"""
Example 4: Advanced Pipeline

Demonstrates complex workflows with IterationManager.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


import snapmark as sm

def main():
    folder = str(ROOT / "examples" / "input")
    folder = r"c:\Users\FEDERICO\Documents\Python_Scripts\Projects\DXF\33-24\Giunti"
    
    # Build custom sequence
    seq = (sm.SequenceBuilder()
           .file_name(trim_start=5)
           #.folder(num_chars=2)
           .build())
    
    print("=== Pipeline: Align + Mark + Count ===")
    
    # Create pipeline manager
    manager = sm.IterationManager(folder, use_backup_system=True)
    
    # Add multiple operations
    manager.add_operation(
        sm.Aligner(),  # Align drawing
        sm.AddMark(seq, scale_factor=100, align='c', max_char=20, min_char=10, down_to=5),  # Add marking
        sm.CountHoles(sm.find_circle_by_radius(min_diam=5, max_diam=10))  # Count holes
    )
    
    # Execute all operations
    stats = manager.execute()
    
    print(f"\n✅ Pipeline completed!")
    print(f"   Processed: {stats['processed']} files")
    print(f"   Modified: {stats['modified']} files")
    
    # Example with single file
    print("\n=== Pipeline on Single File ===")
    
    sm.single_file_pipeline(
        "input/F7.dxf",
        sm.Aligner(),
        sm.AddMark(seq, start_y=.5),
        sm.AddX(sm.find_circle_by_radius(5, 10), x_size=5, x_color=1, x_layer="Engrave"),
        use_backup=True
    )
    
    print("\n✅ Single file pipeline completed!")

if __name__ == "__main__":
    main()