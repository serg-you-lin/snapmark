# SnapMark

SnapMark is a Python library for applying intelligent, customizable text markings and engraving paths on DXF (AutoCAD) files.
It is designed to generate laser-engraving traces (not cutting paths) that make each part identifiable through incised labels, codes, and metadata.
Markings are rendered as **vector segments** (polylines), not DXF text entities — ensuring compatibility with CAM software that reads geometry, not fonts.
Built on top of the excellent [`ezdxf`](https://ezdxf.mozman.at/), it provides a simple API for marking, alignment, hole analysis, and batch processing — tailored for manufacturing, CNC workflows, and automated drawing preparation.

[![PyPI version](https://badge.fury.io/py/snapmark.svg)](https://badge.fury.io/py/snapmark)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ⚠️ Unit & Scale Notice

SnapMark is designed for sheet-metal parts measured in millimeters.

Since DXF files may contain arbitrary units (meters, inches, kilometers, or undefined scale), loading a drawing in a different unit system may produce text markings that appear extremely large, extremely small, or misplaced.

If your DXF is not in millimeters, you must rescale it before processing, or the resulting engraving paths may not match the actual geometry.

## ⚠️ 3D Geometry Notice

SnapMark works exclusively with 2D DXF geometry.
If the drawing contains 3D entities (non-zero Z values, 3D polylines, meshes, solids, or blocks with elevation), SnapMark will refuse processing to avoid unpredictable text placement.

Please ensure your DXF is flattened before use.

---

## Installation
```bash
pip install snapmark
```

## Quick Start
```python
import snapmark as sm

# Mark all DXF files with their filename
sm.mark_by_name(r"path/to/drawings")

# Custom sequence: filename + folder name
seq = (sm.SequenceBuilder()
       .file_name()
       .folder(num_chars=2)   # firts 2 chars of folder name
       .build())

sm.mark_with_sequence(r"path/to/drawings", seq, scale_factor=100)
```

## Features

- ✅ **Simple API** - Mark files in a single function call
- ✅ **Custom sequences** - Combine filename parts, folder names, literals, and custom logic
- ✅ **Automatic Alignment** - Normalize orientation before marking
- ✅ **Batch Processing** - Process folders and subfolders with IterationManager
- ✅ **Backup System** - Automatic .bak creation and restoration
- ✅ **Hole Utilities** - Fast hole detection and counting for quality checks
- ✅ **Extensible Architecture** - Add your own operations and processing steps

## Use Cases

- **Manufacturing**: Add part numbers and quantities to production drawings
- **CAM workflows**: Automatically mark drawings before CNC processing
- **Quality control**: Count holes and verify drawing specifications
- **Batch processing**: Apply consistent markings across large drawing sets

## API Overview (Essentials)

### Shortcuts (Simple Usage)

- `mark_by_name(folder)` - Mark with filename
- `mark_by_split_text(folder, separator, part_index)` - Mark with filename part
- `mark_with_sequence(folder, sequence)` - Mark with custom sequence
- `quick_count_holes(folder, min_diam, max_diam)` - Count holes
- `restore_backup(folder)` - Restore from backups
- `process_single_file(file, *operations)` - Pipeline on single file


### Mark with a custom sequence

For more advanced workflows, you can chain multiple methods together using the SequenceBuilder to create complex, dynamic text marks. This allows you to combine filenames, folder names, static text, and even custom logic into a single sequence.

```python
import snapmark as sm

# Build a complex, custom marking sequence
seq = (sm.SequenceBuilder()
       .file_name()
       .file_part(separator="_", index=0)
       .folder(num_chars=2)
       .literal("TEXT")
       .custom(lambda folder, file: "X")
       .set_separator("-")
       .build())

# Apply this custom sequence to all DXF files in the directory
sm.mark_with_sequence(
    folder=r"C:\DXF",
    sequence=seq,
    scale_factor=100,
)       
```


### Run operations on a single file

If you need to process just a single DXF file instead of an entire folder, you can use the single_file_pipeline function. This allows you to apply the same sequence of operations to an individual file, with the added safety of an automatic backup.

```python
import snapmark as sm

# Create the marking sequence (e.g., using the file name)
seq = sm.SequenceBuilder().file_name().build()

# Run the pipeline on a single specific file
sm.single_file_pipeline(
    r"C:\DXF\part.dxf",    # Path to the target DXF file

    # 1. Automatically align/orient the geometry
    sm.Aligner(),

    # 2. Add the vector marking sequence with custom scaling
    sm.AddMark(
        sequence=seq,
        scale_factor=100,
    ),

    # Safety feature: creates a backup of the original file before modifying it
    use_backup=True
)
```

### Operations (Advanced)

- `AddMark(sequence)` - Add a numeric/alphanumeric marking rendered as **vector segments** (CAM-ready engraving paths)
- `AddText(texts)` - Add a DXF MTEXT entity (native text, not vectors — CAM support may vary)
- `Aligner()` - Aligns the drawing along its longest side in the X direction.
- `CountHoles(find_func)` - Count circles
- `AddX(find_func, x_size)` - Add X marks
- `RemoveCircle(find_func)` - Remove circles
- `SubstituteCircle(find_func, new_radius)` - Replace circles

### Build a custom batch pipeline

You can automatically process multiple DXF files in a folder using the IterationManager. You can stack multiple operations (such as alignment, adding text marks, or trimming lines) to be executed sequentially on every file.

```python
import snapmark as sm

# Initialize the manager with the target directory containing your DXF files
manager = sm.IterationManager(r"C:\DXF")

# Define the sequence of operations to apply to each file
manager.add_operation(
    # 1. Automatically align/orient the DXF geometry
    sm.Aligner(),

    # 2. Add a vector marking sequence (e.g., using the file name as text)
    sm.AddMark(
        sequence=(
            sm.SequenceBuilder()
            .file_name()
            .build()
        )
    ),

    # 3. Trim specific bend lines to optimize for laser cutting or folding
    sm.TrimBendLines(
        layers="Bend",
        start_length=10,
        end_length=10,
        center_length=5,
    ),
)

# Run the pipeline on all files in the directory
manager.execute()
```

### Standalone marking
This feature allows you to generate a new DXF file containing a vector marking sequence and save it directly to a specified directory.

The sequence is built using as the Sequence Builder logic itself, with the exception of file_name() and split_text() which are not supported in this context.

```python
import snapmark as sm

# Define the output directory for the DXF file (must exist)
output_dir = r"C:\YourOutputDir"

# Create the marking sequence
seq = sm.SequenceBuilder().folder().literal("REV1").build()

# Generate and save the standalone mark
sm.StandaloneMark(
    sequence=seq,
    char_height=10,
).save(output_dir)

```

📘 Documentation:
(Documentation files will be available in the docs/ directory.)


## Requirements

- Python 3.10+
- ezdxf >= 1.0.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Federico Sidraschi**  
[LinkedIn](https://www.linkedin.com/in/federico-sidraschi-059a961b9/) | [GitHub](https://github.com/serg-you-lin)

## Acknowledgments

Built with [ezdxf](https://ezdxf.mozman.at/) - the excellent DXF library for Python.

## Examples

SnapMark comes with a set of ready-to-run examples located in the `examples/` folder.  
These examples demonstrate common operations, including restoring backups, counting holes, and basic marking.  

---

**Keywords**: DXF, CAD, AutoCAD, marking, automation, batch processing, manufacturing, CNC, CAM