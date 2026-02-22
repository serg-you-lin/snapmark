# Shortcuts

SnapMark provides high-level convenience functions for common operations.
These shortcuts encapsulate complete pipelines and are ideal for quick scripts or simple automation tasks.

All shortcuts can process **both single files and entire folders**.

---

## `mark_by_name(file_or_folder, **kwargs)`

Marks DXF files using the full filename (without extension) as the marking text.

**Parameters:**
- `file_or_folder` (str): Path to a DXF file or folder containing DXF files
- `align` (str): Text alignment - 'l' (left), 'c' (center), 'r' (right). Default: 'c'
- `min_char` (int): Minimum character height. Default: 5
- `max_char` (int): Maximum character height. Default: 20
- `start_y` (float): Starting Y coordinate for search. Default: 1
- `**kwargs`: Additional parameters accepted by `AddMark` (see `parameters.md`)
  - Common: `scale_factor`, `space`, `mark_layer`, `mark_color`, `excluded_layers`, `arbitrary_x`, `arbitrary_y`

**Example:**
```python
import snapmark as sm

# Single file
sm.mark_by_name("part.dxf")

# Folder with custom alignment and size
sm.mark_by_name("drawings/", align='l', min_char=8, max_char=15)

# With scale factor and custom layer
sm.mark_by_name("drawings/", scale_factor=150, mark_layer='LABEL')
```

**Use case:** Quick identification when filenames already contain product codes.

---

## `mark_by_splitted_text(file_or_folder, separator='_', part_index=0, **kwargs)`

Marks using a specific portion of the filename, split by a separator character.

Useful when filenames contain structured information (e.g., `PART_123_5mm.dxf`).

**Parameters:**
- `file_or_folder` (str): Path to file or folder
- `separator` (str): Character/string used to split the filename. Default: '_'
- `part_index` (int): Index of the part to extract (0-based). Default: 0
- `align` (str): Text alignment. Default: 'c'
- `min_char` (int): Minimum character height. Default: 5
- `max_char` (int): Maximum character height. Default: 20
- `start_y` (float): Starting Y coordinate. Default: 1
- `**kwargs`: Additional `AddMark` parameters (see `parameters.md`)

**Example:**
```python
import snapmark as sm

# File: "S532_P5_SP4_Q2.dxf" → marks "S532"
sm.mark_by_splitted_text("drawings/", separator='_', part_index=0)

# File: "PROD-A123-REV2.dxf" → marks "A123"
sm.mark_by_splitted_text("drawings/", separator='-', part_index=1)

# With custom parameters
sm.mark_by_splitted_text("drawings/", 
                         separator='_', 
                         part_index=0,
                         align='r',
                         min_char=10,
                         scale_factor=120)
```

**Use case:** Extracting product codes from structured filenames following company naming conventions.

---

## `mark_with_sequence(file_or_folder, sequence, **kwargs)`

Marks files using a custom sequence built with `SequenceBuilder`.

**Parameters:**
- `file_or_folder` (str): Path to file or folder
- `sequence` (Sequence): Sequence object created with `SequenceBuilder`
- `align` (str): Text alignment. Default: 'c'
- `min_char` (int): Minimum character height. Default: 5
- `max_char` (int): Maximum character height. Default: 10
- `start_y` (float): Starting Y coordinate. Default: 1
- `**kwargs`: Additional `AddMark` parameters (see `parameters.md`)

**Example:**
```python
import snapmark as sm

# Simple sequence: filename + folder name
seq = (sm.SequenceBuilder()
       .file_name()
       .folder(num_chars=2)
       .build())

sm.mark_with_sequence("drawings/", seq, align='c', min_char=8)

# Complex sequence with custom logic
import re

def extract_revision(folder, filename):
    match = re.search(r'REV(\d+)', filename)
    return f"R{match.group(1)}" if match else "R0"

seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)
       .custom(extract_revision)
       .set_separator("-")
       .build())

sm.mark_with_sequence("drawings/", seq, scale_factor=120)
```

**Use case:** Complex marking logic combining multiple elements (see `sequences.md` for details).

---

## `quick_count_holes(file_or_folder, min_diam=0, max_diam=float('inf'), **kwargs)`

Counts circles (holes) within a diameter range and returns aggregated statistics.

**Parameters:**
- `file_or_folder` (str): Path to file or folder
- `min_diam` (float): Minimum diameter (inclusive). Default: 0
- `max_diam` (float): Maximum diameter (inclusive). Default: infinity
- `multiplier` (callable, optional): Function that extracts a quantity multiplier from the filename
- `verbose` (bool): If True, prints per-file details. Default: False

**Returns:**
- `dict`: Statistics dictionary with keys:
  - `'total_count'`: Total number of holes
  - `'processed'`: Number of files processed
  - `'errors'`: List of files with errors
  - Additional counter-specific data

**Basic example:**
```python
import snapmark as sm

# Count holes between 5mm and 10mm diameter
stats = sm.quick_count_holes("drawings/", min_diam=5, max_diam=10)
print(f"Total holes found: {stats['total_count']}")
print(f"Files processed: {stats['processed']}")
```

**Example with multiplier:**
```python
import re
import snapmark as sm

def extract_quantity(filename):
    """Extracts quantity from names like 'PART_Q5.dxf'"""
    match = re.search(r'Q(\d+)', filename)
    return int(match.group(1)) if match else 1

stats = sm.quick_count_holes(
    "drawings/", 
    min_diam=5, 
    max_diam=10,
    multiplier=extract_quantity,
    verbose=True  # Show per-file counts
)
print(f"Total holes (accounting for quantities): {stats['total_count']}")
```

**Use case:** Pre-production quality control, design consistency verification, drilling time estimation.

---

## `restore_backup(file_or_folder, delete_backups=True, recursive=False)`

Restores original DXF files from `.bak` backup files.

**Parameters:**
- `file_or_folder` (str): Path to file or folder
- `delete_backups` (bool): If True, deletes `.bak` files after restoration. Default: True
- `recursive` (bool): If True, processes subfolders as well. Default: False

**Returns:**
- `dict`: Restoration statistics

**Example:**
```python
import snapmark as sm

# Restore all files in folder
sm.restore_backup("drawings/")

# Restore recursively but keep backup files
sm.restore_backup("drawings/", recursive=True, delete_backups=False)

# Restore single file
sm.restore_backup("part.dxf")
```

**Warning:** This operation **overwrites** existing DXF files with their backups!

**Use case:** Undo erroneous batch operations, restore after testing.

---

## `single_file_pipeline(file_path, *operations, use_backup=True)`

Executes a sequence of operations on a single DXF file.

**Parameters:**
- `file_path` (str): Path to the DXF file
- `*operations`: Sequence of Operation objects to execute
- `use_backup` (bool): If True, creates backup before modifying. Default: True

**Returns:**
- `dict`: Processing statistics with keys:
  - `'file'`: File path processed
  - `'modified'`: Whether the file was modified
  - `'operations_count'`: Number of operations executed

**Example:**
```python
import snapmark as sm

seq = sm.SequenceBuilder().file_name().build()

# Execute multiple operations in sequence
sm.single_file_pipeline(
    "test_part.dxf",
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=100),
    sm.CountHoles(sm.find_circle_by_radius(5, 10)),
    sm.AddX(sm.find_circle_by_radius(3, 5), x_size=6),
    use_backup=True
)
```

**Use case:** Interactive testing, debugging new operations, one-off file processing.

---

## General Notes

**File vs Folder Processing:**
All marking and counting shortcuts automatically detect whether the input is a single file or a folder and process accordingly.

**Backup System:**
Operations that modify files create `.bak` backups automatically (can be disabled via `use_backup=False` in `single_file_pipeline` or through kwargs in other functions).

**Error Handling:**
If a file causes errors during processing, it is skipped and processing continues with remaining files.

**Operation Parameters:**
For detailed information on parameters accepted by underlying operations (like `AddMark`, `CountHoles`), see `parameters.md`.

---

**Next steps:**
- For complex marking logic → see `sequences.md`
- For custom pipelines → see `pipeline.md`
- For advanced positioning parameters → see `parameters.md`