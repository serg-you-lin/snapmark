# Parameters - Basic operations

## AddMark
Adds numerical markings to DXF files.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sequence` | `Sequence` | Object that provides the sequence text for marking. | **Required** |
| `scale_factor` | `float` | Scaling factor for the marking size. | 50 |
| `space` | `float` | Space between characters in the sequence. | 1.5 |
| `min_char` | `int` | Minimum characters dimension allowed (in mm). | 5 |
| `max_char` | `int` | Maximum characters dimension allowed (in mm). | 20 |
| `arbitrary_x` | `float` or `None` | X coordinate for manual positioning. | None |
| `arbitrary_y` | `float` or `None` | Y coordinate for manual positioning. | None |
| `align` | `str` | Alignment of the text ('c', 'l', 'r'). | 'c' |
| `start_y` | `float` | Y position to start marking. | 1 |
| `step` | `float` | Vertical distance re-placement sequence (when previous positioning attempt fails). | 2 |
| `margin` | `float` | Margin around the sequence. | 1 |
| `down_to` | `float` or `None` | Additional lower limit for the minimum allowed character dimension, only used when the sequence fails to be placed using the standard min_char constraint. | None |
| `mark_layer` | `str` | Layer where markings are added. | 'MARK' |
| `mark_color` | `str` | DXF color index of marking (ACI). | None |
| `excluded_layers` | `list[str]` or `None` | Layers to not consider to compute marking position. | None |

---

## SubstituteCircle
Replaces circles with new radius or diameter.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `find_circle_function` | `Callable` | Function to find existing circles in the DXF. | **Required** |
| `new_radius` | `float` or `None` | New radius for replacement circles. | None |
| `new_diameter` | `float` or `None` | New diameter for replacement circles. | None |
| `layer` | `str` | Layer to place new circles. | '0' |
| `layer` | `str` | DXF color index of new circles (ACI). | 'None' |

> Either `new_radius` or `new_diameter` **must** be provided.

---

## AddX
Adds an "X" at circle locations.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `find_circle_function` | `Callable` | Function to find circles. | **Required** |
| `x_size` | `float` | Size of the X to add. | 8 |
| `layer` | `str` | Layer where the X is added. | 'MARK' |
| `x_color` | `int` | DXF color index of the X (ACI).    | 'None'    |
| `delete_hole` | `bool` | Whether to delete the original circle. | True |

---

## RemoveCircle
Removes circles from the file.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `find_circle_function` | `Callable` | Function to find circles to delete. | **Required** |

---

## RemoveLayer
Removes a specific layer.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `layer` | `str` | Name of the layer to delete. | **Required** |


---

## Operation.execute_single

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `file_path` | `str` | Full path to the DXF file. | **Required** |
| `use_backup` | `bool` | Whether to create a backup before editing. | True |

---

## Operation.process_folder

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `folder_path` | `str` | Path of the folder containing DXF files. | **Required** |
| `operation_instance` | `Operation` | Instance of the operation to apply. | **Required** |
| `use_backup` | `bool` | Whether to backup each file. | True |
| `recursive` | `bool` | Search subfolders recursively. | False |
| `file_pattern` | `str` | Glob pattern to filter files. | "*.dxf" |


## Aligner
Aligns entities in a DXF file based on the longest line.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| None | N/A | This operation does not take external parameters. | N/A |

**Notes:**
- `create_new`: Internal flag to indicate whether a new alignment was applied (default True).  
- Alignment is performed along the X-axis based on the longest line in the file.  
- Only `LINE`, `ARC`, `CIRCLE`, and `ELLIPSE` entities are supported; others are ignored.  
- If no lines are found, alignment is not performed.  

---

## Aligner.execute

| Parameter | Type | Description |
|-----------|------|-------------|
| `doc` | `ezdxf.DXFDocument` | The DXF document to align. |
| `folder` | `str` | Path to the folder containing the DXF file (not used internally). |
| `file_name` | `str` | Name of the DXF file (not used internally). |

**Returns:**  
`bool` – True if the alignment was applied.

---

## Aligner.flip_file

| Parameter | Type | Description |
|-----------|------|-------------|
| `msp` | `Modelspace` | Modelspace containing entities. |
| `lines` | `list` | List of line entities. |
| `arcs` | `list` | List of arc entities. |
| `circles` | `list` | List of circle entities. |
| `ellipses` | `list` | List of ellipse entities. |
| `pp` | `tuple[float, float]` | Pivot point for rotation. |
| `longer_side` | `Entity` | The longest line used to determine rotation. |

**Notes:** Rotates all entities 180° if the longest line is oriented in the opposite direction.

---

# Parameters - Counter Operations Module

## Counter
Base class for counting operations.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| None | N/A | Counter operations do not take external parameters. | N/A |

**Attributes:**
- `counter` (int): Current count (default 0).  
- `create_new` (bool): Always False, counters do not modify files.  
- `is_processing_folder` (bool): Internal flag for folder processing.  

**Notes:**
- Counter operations never modify files, so backup is ignored.  
- Subclasses must implement `execute()` and `count_message()`.

---

## Counter.execute_single

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `file_path` | `str` | Full path to a DXF file. | N/A |
| `use_backup` | `bool` | Ignored (Counter does not modify files). | False |
| `print_message` | `bool` | Whether to print the count message after processing. | True |

**Returns:**  
`bool` – Always False (files are not modified).

---

## Counter.process_folder

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `folder_path` | `str` | Path to the folder containing DXF files. | N/A |
| `operation_instance` | `Counter` | Instance of the Counter subclass. | N/A |
| `use_backup` | `bool` | Ignored (Counter does not modify files). | False |
| `recursive` | `bool` | Process subfolders as well. | False |
| `file_pattern` | `str` | File pattern to filter (default `"*.dxf"`). | `"*.dxf"` |

**Returns:**  
`dict` – Statistics dictionary containing:
- `'processed'`: Number of files processed
- `'modified'`: Always 0
- `'errors'`: List of files with errors
- `'total_count'`: Total count from the counter

---

## CountFiles
Counts how many DXF files are present in the folder.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| None | N/A | Uses internal counter increment per file. | N/A |

**Notes:**  
- `execute()` increments counter by 1 per file.  
- `count_message()` prints: `"✓ Total files in the folder: X"`.

---

## CountHoles
Counts circles (holes) in DXF files.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `find_circle_function` | callable | Function that returns circle entities from a DXF document. | N/A |
| `mess` | bool | If True, prints per-file hole count. | False |

**Methods:**
- `mult(function)`: Apply a multiplier function based on file name. Useful to account for quantities encoded in file names.

**Notes:**
- `execute()` counts holes in the current file and adds to `counter`.  
- `message()` prints per-file count if `mess=True`.  
- `count_message()` prints: `"✓ Total holes: X"`.  

---

## Helper Functions

### `count_holes`
| Parameter | Type | Description |
|-----------|------|-------------|
| `holes` | iterable | Iterable of hole (circle) entities. |

**Returns:**  
`int` – Number of holes.





