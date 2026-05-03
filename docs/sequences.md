# Sequences

This module covers two complementary builders:

| Builder | Produces | Used by |
|---|---|---|
| `SequenceBuilder` | A single vektor marking string | `AddMark` |
| `TextBuilder` | A list of text annotations lines | `AddText` |

Both follow the same composable pattern: chain methods, call `.build()`, pass to the operation.

---

## Core Concept

A sequence is a "recipe" that tells SnapMark how to build the marking text for each file.

**Analogy:** Think of `SequenceBuilder` as a modular string assembler:
- Each `.method()` adds a "piece" to the final string
- `.set_separator()` decides how to join the pieces
- `.build()` freezes the recipe into an executable sequence

---

## SequenceBuilder API

### Constructor
```python
seq = sm.SequenceBuilder()
```

### Composition Methods

#### `.file_name(trim_start=0, trim_end=0)`
Adds the filename (without `.dxf` extension). Allows trimming characters from the start/end of the filename.

```python
seq = sm.SequenceBuilder().file_name().build()
# File: "PART_123.dxf" → Output: "PART_123"
```

---

#### `.split_text(separator: str, part_index: int)`
Splits the filename using `separator` and extracts the part at the specified index.

**Parameters:**
- `separator`: Character/string used for splitting
- `part_index`: Zero-based index of the part to extract

```python
seq = (sm.SequenceBuilder()
       .split_text(separator='_', part_index=0)
       .build())
# File: "S532_P5_Q2.dxf" → Output: "S532"
```

**Error handling:** If the index doesn't exist, returns an empty string.

---

#### `.folder(num_chars: int = None, level: int = 0)`
Adds the name of the containing folder.

**Parameters:**
- `num_chars` (optional): Number of leading characters to take
- `level` (optional, default = 0): Specifies which folder to use relative to the file location: 0 -> parent folder, 1 -> parent of the parent, and so on.

```python
# Full folder name
seq = sm.SequenceBuilder().folder().build()
# File in "Production2024/" → Output: "Production2024"

# Only first 2 characters
seq = sm.SequenceBuilder().folder(num_chars=2).build()
# File in "Production2024/" → Output: "Pr"

# Deeper folder example:
# File at "/Projects/BatchA/Drawings/part.dxf"
# level=1 → "BatchA"
seq = sm.SequenceBuilder().folder(level=1).build()
```

---

#### `.literal(text: str)`
Adds fixed text.

```python
seq = (sm.SequenceBuilder()
       .literal("REV")
       .literal("3")
       .build())
# Output: "REV-3" (assuming default separator "-")
```

**Use case:** Standard prefixes/suffixes, department codes, version numbers.

---

#### `.custom(func: Callable[[str, str], str])`
Adds the result of a custom function.

**Function signature:**
```python
def my_function(folder_path: str, filename: str) -> str:
    # folder_path: full path to containing folder
    # filename: filename with extension
    return "result"
```

**Example - Quantity extraction:**
```python
import re

def extract_quantity(folder, filename):
    match = re.search(r'Q(\d+)', filename)
    return f"Q{match.group(1)}" if match else "Q1"

seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)
       .custom(extract_quantity)
       .build())
# File: "S532_P5_Q3.dxf" → Output: "S532-Q3"
```

**Example - Timestamp:**
```python
from datetime import datetime

def add_date(folder, filename):
    return datetime.now().strftime("%Y%m%d")

seq = (sm.SequenceBuilder()
       .file_name()
       .custom(add_date)
       .build())
# Output: "PART_123-20251206" (if you run the process on 06 Dec 2025)
```

---

#### `.set_separator(sep: str)`
Sets the character used to join pieces (default: `"-"`).

```python
seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)
       .file_part(separator='_', part_index=1)
       .set_separator("_")  # Use underscore instead of dash
       .build())
# File: "S532_P5_Q2.dxf" → Output: "S532_P5"
```

---

#### `.build()`
Finalizes and returns a `Sequence` object usable in operations.

```python
seq = sm.SequenceBuilder().file_name().build()
# Now 'seq' is ready to be passed to AddMark or mark_with_sequence
```

---

## Common Patterns

### 1. Product code from structured filename
```python
# Convention: "CODE_REVISION_MATERIAL.dxf"
seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)  # Code
       .file_part(separator='_', part_index=1)  # Revision
       .build())
# "P1234_R2_INOX.dxf" → "P1234-R2"
```

### 2. Code + Production batch (from folder)
```python
# Structure: /Batches/LOT2024A/drawings/part.dxf
seq = (sm.SequenceBuilder()
       .folder(num_chars=4, level=1)  # "LOT2"
       .file_name()
       .build())
# Output: "LOT2-part"
```

### 3. Fixed prefix + part number
```python
seq = (sm.SequenceBuilder()
       .literal("MFG")
       .file_part(separator='-', part_index=1)
       .build())
# "PROD-A123-X.dxf" → "MFG-A123"
```

### 4. Conditional custom logic
```python
def material_code(folder, filename):
    if "INOX" in filename.upper():
        return "SS"
    elif "ALUMINUM" in filename.upper():
        return "AL"
    return "ST"

seq = (sm.SequenceBuilder()
       .file_name()
       .custom(material_code)
       .build())
# "FLANGE_INOX.dxf" → "FLANGE_INOX-SS"
```

### 5. Complex multi-part extraction
```python
import re

def extract_part_info(folder, filename):
    """Extract part number from format: S532_P5_SP4_Q2.dxf"""
    match = re.search(r'P(\d+)', filename)
    return f"P{match.group(1)}" if match else ""

seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)  # "S532"
       .custom(extract_part_info)               # "P5"
       .literal("REV1")
       .build())
# Output: "S532-P5-REV1"
```

---

## Usage in Operations

### With shortcuts
```python
seq = sm.SequenceBuilder().file_name().build()
sm.mark_with_sequence("drawings/", seq, scale_factor=100)
```

### With pipelines
```python
seq = (sm.SequenceBuilder()
       .file_part(separator='_', part_index=0)
       .folder(num_chars=2)
       .build())

manager = sm.IterationManager("drawings/", use_backup_system=True)
manager.add_operation(
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=120)
)
manager.execute(recursive=True)
```

### Single file
```python
seq = sm.SequenceBuilder().literal("TEST").file_name().build()
sm.single_file_pipeline(
    "part.dxf",
    sm.AddMark(seq, scale_factor=100)
)
```

---

## Advanced Notes

**Piece ordering:** Pieces are concatenated in the order methods are called.

**Empty pieces:** If a method returns an empty string (e.g., `part_index` out of range), the piece is ignored during concatenation.

**Final separator:** Not added after the last piece.

**Immutability:** After `.build()`, the sequence is immutable. Create new `SequenceBuilder` instances for variations.

**Error resilience:** Custom functions that throw exceptions will cause the operation to skip that file with an error message.

---

## Built-in Sequence Factories

SnapMark also provides factory functions for common sequences:

```python
from snapmark.sequence.sequence_system import from_file_name, from_splitted_text

# Equivalent to SequenceBuilder().file_name().build()
seq1 = from_file_name(trim_start=0, trim_end=0)

# Equivalent to SequenceBuilder().file_part(sep, idx).build()
seq2 = from_split_text(separator='_', part_index=0, trim_start=0, trim_end=0)
```

These are used internally by `mark_by_name()` and `mark_by_split_text()` shortcuts.

---

---

## TextBuilder

`TextBuilder` is the counterpart of `SequenceBuilder` for `AddText` — it builds a list of text lines instead of a single marking string.

**Analogy:** If `SequenceBuilder` assembles a single engraving string, `TextBuilder` assembles a multi-line label — like composing the lines of a post-it note attached to the drawing.

### Constructor
```python
tb = sm.TextBuilder()
```

### Composition Methods

#### `.static(text: str)`
Adds a fixed text line.

```python
tb = sm.TextBuilder().static("MAT: S235JR").static("REV: 1").build()
```

---

#### `.line(func: Callable[[str, str], str])`
Adds a dynamic line computed from a function.

**Function signature:**
```python
def my_line(folder_path: str, filename: str) -> str:
    return "result"
```

```python
tb = (sm.TextBuilder()
      .line(lambda folder, f: f"FILE: {f}")
      .static("REV: 1")
      .build())
```

---

#### `.build()`
Finalizes and returns a `ComposedText` object usable in `AddText`.

```python
tb = sm.TextBuilder().static("NOTE: OK").build()
# Now 'tb' is ready to be passed to AddText
```

**Note:** Raises `ValueError` if no lines have been defined.

---

### Common Patterns

#### Static annotation
```python
tb = (sm.TextBuilder()
      .static("MAT: S235JR")
      .static("FINITURA: GREZZA")
      .build())
```

#### Dynamic lines from filename
```python
import re

def extract_material(folder, filename):
    match = re.search(r'(S235|S355|INOX)', filename.upper())
    return f"MAT: {match.group(1)}" if match else "MAT: ND"

tb = (sm.TextBuilder()
      .line(extract_material)
      .static("REV: 1")
      .build())
```

#### Used in pipeline with AddMark
```python
seq = sm.SequenceBuilder().file_name().build()
tb = sm.TextBuilder().static("MAT: S235JR").build()

manager = sm.IterationManager("drawings/", use_backup_system=True)
manager.add_operation(
    sm.Aligner(),
    sm.AddMark(seq, scale_factor=100),  # vector marking
    sm.AddText(tb, char_height=3)       # text annotation
)
manager.execute()
```


**Next steps:**
- To apply sequences in batch → see `pipeline.md`
- For positioning parameters → see `parameters.md`
- For one-liner functions → see `shortcuts.md`