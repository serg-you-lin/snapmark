# Pipeline

Pipelines define **how** to process files: which operations to execute, in what order, and on which files.

SnapMark offers two approaches:
1. **Shortcuts** → pre-packaged pipelines (see `shortcuts.md`)
2. **IterationManager** → custom pipelines with granular control

---

## Pipeline Concept

**Analogy:** A pipeline is like an industrial assembly line:
- Each **Operation** is a workstation
- The **DXF file** is the piece moving through stations
- **IterationManager** is the conveyor belt coordinating the flow

Operations are executed **sequentially** on each file, in the specified order.

---

## IterationManager

Main class for building custom batch pipelines.

### Constructor
```python
manager = sm.IterationManager(
    folder_path: str,
    use_backup_system: bool = True
)
```

**Parameters:**
- `folder_path`: Root folder containing DXF files
- `use_backup_system`: If True, creates `.bak` before modifying files

---

### `.add_operation(*operations)`
Adds one or more operations to the pipeline.

```python
manager = sm.IterationManager("drawings/")
manager.add_operation(
    sm.Aligner(),
    sm.AddMark(sequence, scale_factor=100)
)
```

**Order matters:** Operations execute in the order they're added.

---

### `.execute(recursive=False)`
Executes the pipeline on all DXF files.

**Parameters:**
- `recursive`: If True, processes subfolders as well

```python
manager.execute()                    # Current folder only
manager.execute(recursive=True)      # Include subfolders
```

**Behavior:**
- Each file is processed independently
- Errors on one file don't block others
- Progress and statistics printed to stdout

---

## Available Operations

### `Aligner()`
Normalizes drawing orientation by aligning the longest side along the X-axis.

```python
sm.Aligner()
```

**When to use:** Before marking or analysis to ensure consistent orientation.

**See `parameters.md`** for technical details on supported entity types and rotation logic.

---

### `AddMark(sequence, **kwargs)`
Adds text marking to the drawing.

**Parameters:**
- `sequence`: Sequence object from `SequenceBuilder`
- For all other parameters (scale_factor, align, min_char, max_char, mark_layer, etc.) → see `parameters.md`

```python
seq = sm.SequenceBuilder().file_name().build()
sm.AddMark(seq, scale_factor=120, align='l', mark_layer='ENGRAVE', mark_color=5)
```

### `AddText(text_sequence, **kwargs)`
Adds native DXF MTEXT entities to the drawing. Unlike `AddMark`, text is not rendered as vector segments — CAM support may vary.

**Parameters:**
- `text_sequence`: ComposedText object from `TextBuilder`
- For all other parameters (char_height, align, text_layer, text_color, etc.) → see `parameters.md`

```python
text = sm.TextBuilder().literal("PRODOTTO: acciaio").build()
sm.AddText(text, char_height=3, align='l', text_layer='INFO')
```

### `CountHoles(find_function, mess=False)`
Counts circles matching specified criteria.

**Parameters:**
- `find_function`: Function identifying circles to count
- `mess`: If True, prints per-file count (default: False)

**See `parameters.md`** for details on the `.mult()` method for quantity multipliers.

```python
# Count holes between 5-10mm diameter
sm.CountHoles(sm.find_circle_by_radius(5, 10))

# With verbose output
sm.CountHoles(sm.find_circle_by_radius(5, 10), mess=True)
```

**Output:** Prints count per file.

---

### `AddX(find_function, x_size=8, **kwargs)`
Replaces circles with "X" marks (for manual drilling).

**Parameters:**
- `find_function`: Circle selection function
- `x_size`: Size of the X mark (default: 8)
- For layer, delete_hole parameters → see `parameters.md`

```python
# Mark small holes for manual drilling
sm.AddX(sm.find_circle_by_radius(3, 6), x_size=5, x_layer='MANUAL', x_color=1)
```

---

### `RemoveCircle(find_function)`
Removes circles matching criteria.

```python
# Remove centering holes (small)
sm.RemoveCircle(sm.find_circle_by_radius(1, 3))
```

---

### `SubstituteCircle(find_function, new_radius=None, new_diameter=None, layer='0')`
Replaces circles with new circles of specified size.

**Parameters:**
- `find_function`: Circle selection function
- `new_radius` or `new_diameter`: New size (provide one)
- `layer`: Layer for new circles (default: '0')

**See `parameters.md`** for full parameter details.

```python
# Standardize holes to 5mm radius
sm.SubstituteCircle(sm.find_circle_by_radius(4.8, 5.2), new_radius=6.5)
```

---

### `RemoveLayer(layer)`
Removes an entire layer from the drawing.

```python
# Remove construction layer
sm.RemoveLayer('HOLES')
```

---

## Find Functions

Helper functions to identify circles for processing.

### `find_circle_by_radius(min_radius, max_radius)`
Returns a function that selects circles within a radius range.

```python
find_func = sm.find_circle_by_radius(5, 10)
# Selects circles with radius between 5-10mm (diameter 10-20mm)
```

**Note:** Parameters are in millimeters, referring to **radius** (not diameter).

---

## Usage Patterns

### 1. Basic Pipeline: Align + Mark
```python
seq = sm.SequenceBuilder().file_name().build()

manager = sm.IterationManager("drawings/", use_backup_system=True)
manager.add_operation(
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=100)
)
manager.execute()
```

---

### 2. Complete Pipeline: Prepare for Production
```python
seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)
       .folder(num_chars=3)
       .build())

manager = sm.IterationManager("production/", use_backup_system=True)
manager.add_operation(
    sm.Aligner(),                                    # Normalize orientation
    sm.CountHoles(sm.find_circle_by_radius(5, 10)), # Verify holes
    sm.AddMark(seq, scale_factor=120),               # Add product code
    sm.AddX(sm.find_circle_by_radius(3, 5), x_size=6, x_color=3) # Mark small holes with cyan 'X' symbols
)
manager.execute(recursive=True)
```

---

### 3. Recursive Pipeline: Process Complex Folder Structure
```python
# Structure: /projects/PROJECT_A/batches/LOT001/drawings/*.dxf

seq = (sm.SequenceBuilder()
       .folder(num_chars=4)  # First 4 chars of batch folder
       .file_name()
       .build())

manager = sm.IterationManager("projects/", use_backup_system=True)
manager.add_operation(
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=100)
)
manager.execute(recursive=True)  # Process all subtrees
```

---

### 4. Conditional Pipeline: Custom Logic in Sequence
```python
import re

def extract_and_validate(folder, filename):
    """Extract code only if valid, otherwise return WARNING"""
    match = re.search(r'P(\d{4})', filename)
    if match:
        return f"P{match.group(1)}"
    return "WARN"

seq = (sm.SequenceBuilder()
       .custom(extract_and_validate)
       .build())

manager = sm.IterationManager("drawings/")
manager.add_operation(sm.AddMark(seq, scale_factor=100))
manager.execute()
```

---

### 5. Multi-Stage: Separate Pipelines for Different Phases
```python
# Phase 1: Preparation
manager1 = sm.IterationManager("raw/", use_backup_system=True)
manager1.add_operation(
    sm.Aligner(),
    sm.RemoveCircle(sm.find_circle_by_radius(1, 2))  # Remove centering holes
)
manager1.execute()

# Phase 2: Marking
seq = sm.SequenceBuilder().file_name().build()
manager2 = sm.IterationManager("raw/", use_backup_system=False)  # Backup already done in phase 1
manager2.add_operation(sm.AddMark(seq, scale_factor=100))
manager2.execute()
```

---

### 6. Quality Control Pipeline: Count and Verify
```python
import re

def get_quantity(filename):
    """Extract quantity from filename like 'PART_Q5.dxf'"""
    match = re.search(r'Q(\d+)', filename)
    return int(match.group(1)) if match else 1

counter = sm.CountHoles(sm.find_circle_by_radius(5, 10), mess=True)
counter.mult(get_quantity)  # Apply quantity multiplier

manager = sm.IterationManager("drawings/")
manager.add_operation(counter)
stats = manager.execute()

print(f"Total holes across all parts: {stats['total_count']}")
```

---

### 7. Mark + Metadata: Vector Marking and Text Annotation
```python
seq = sm.SequenceBuilder().file_name().build()
text = sm.TextBuilder().literal("MAT: S235JR").build()

manager = sm.IterationManager("drawings/", use_backup_system=True)
manager.add_operation(
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=100),   # CAM-ready vector marking
    sm.AddText(text, char_height=3)      # Human-readable annotation
)
manager.execute()
```


## Single File Pipeline

For testing or interactive processing, use `single_file_pipeline`:

```python
seq = sm.SequenceBuilder().file_name().build()

sm.single_file_pipeline(
    "test_part.dxf",
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=100),
    sm.CountHoles(sm.find_circle_by_radius(5, 10)),
    use_backup=True
)
```

**When to use:**
- Debugging new operations
- Verifying parameters before batch processing
- One-off processing on specific file

---

## Best Practices

### 1. Operation Order
Recommended logical order:
1. `Aligner()` → normalize first
2. Removal/substitution operations → clean geometry
3. `CountHoles()` → verify before marking
4. `AddMark()` → mark after geometry is finalized
5. `AddX()` → add final markings

### 2. Backup Strategy
Always use `use_backup_system=True` for destructive operations. Disable only if:
- You have external backups
- Operations are idempotent
- Subsequent phase of multi-stage (backup already created)

### 3. Incremental Testing
Test complex pipelines on file subsets first:
```python
# Test on 3 files
manager = sm.IterationManager("drawings/test_subset/")
manager.add_operation(...)
manager.execute()

# If OK, scale to full set
manager = sm.IterationManager("drawings/")
manager.add_operation(...)
manager.execute(recursive=True)
```

### 4. Logging
Capture output for audit trails:
```python
import sys

with open("processing_log.txt", "w") as log:
    sys.stdout = log
    manager.execute()
    sys.stdout = sys.__stdout__  # Restore
```

### 5. Error Recovery
If something goes wrong, use `sm.restore_backup()` to restore original state:
```python
# Restore all files in folder
sm.restore_backup("drawings/")

# Restore recursively
sm.restore_backup("drawings/", recursive=True)
```

---

## Error Handling

**Default behavior:**
- Corrupted/malformed file → skip and continue
- Operation fails → log error, skip file, continue
- Pipeline never stops for individual file errors

**Recovery:**
If processing fails, use `sm.restore_backup()` to restore to original state.

**Statistics:**
`execute()` returns a dict with processing statistics:
```python
stats = manager.execute()
print(f"Processed: {stats['processed']}")
print(f"Modified: {stats['modified']}")
print(f"Errors: {len(stats['errors'])}")
```

---

## Advanced: Custom Operations

You can create custom operations by subclassing the `Operation` base class:

```python
from snapmark.operations.basic_operations import Operation

class MyCustomOperation(Operation):
    def __init__(self, param1, param2):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
        self.create_new = True  # Set to True if modifying files
    
    def execute(self, doc, folder, file_name):
        # Your custom logic here
        # doc: ezdxf.DXFDocument
        # folder: str (folder path)
        # file_name: str (filename)
        
        # Return True if file was modified, False otherwise
        return self.create_new

# Use in pipeline
manager = sm.IterationManager("drawings/")
manager.add_operation(MyCustomOperation("value1", "value2"))
manager.execute()
```

For Counter operations (non-modifying), subclass `Counter` instead and implement `count_message()`.

---

**Next steps:**
- To build complex sequences → see `sequences.md`
- For advanced positioning parameters → see `parameters.md`
- For one-liner functions → see `shortcuts.md`