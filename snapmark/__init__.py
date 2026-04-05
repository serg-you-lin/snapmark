"""
SnapMark - Library for marking and manipulating DXF files.

Basic Usage:
    import snapmark as sm
    
    # Quick mark by file name
    sm.mark_by_name("Examples/Input")
    
    # Mark folder
    sm.Operation.process_folder("folder", mark)
    
    # Multiple pipeline example
    manager = sm.IterationManager("folder")
    manager.add_operation(
        sm.Aligner(),
        sm.AddMark(sequence),
        sm.CountHoles(sm.find_circle_by_radius(5, 10))
    )
    manager.execute()
"""

# ========== CORE: Main operations ==========
from .operations.basic_operations import (
    Operation,
    AddMark,
    SubstituteCircle,
    AddX,
    RemoveCircle,
    RemoveLayer,
    PrintLayers,
)

from .operations.counter import (
    Counter,
    CountFiles,
    CountHoles,
)

from .operations.aligner import Aligner

# ========== SEQUENCE (NEW SYSTEM) ==========
from .sequence.sequence_system import (
    SequenceBuilder,
    from_file_name,
    from_splitted_text
)

# ========== SEQUENCE (OLD - DEPRECATED) ==========
from .sequence.sequence_legacy import (
    Conc,
    FixSeq,
)

# ========== SHORTCUTS ========== 
from .shortcuts import (
    mark_by_name,
    mark_by_splitted_text,
    mark_with_sequence,
    quick_count_holes,
    single_file_pipeline,  
    restore_backup
)


# ========== ITERATION MANAGER ==========
from .core import IterationManager, iteration_manager  # iteration_manager = alias legacy

# ========== UTILITIES ==========
from .utils.backup_manager import BackupManager
from .utils.helpers import (
    count_holes,
    find_all_circles,
    find_circle_by_radius,
)

# ========== CHECKING/SEARCH ==========
from .checking.checking import (
    find_spec_holes,
    find_circle_centers,
    print_layers as print_document_layers,
    print_entities,
)


# ========== METADATA ==========
__version__ = "2.0.7"
__author__ = "serg_you_lin"
__all__ = [
    # Shortcuts (main API)
    'mark_by_name',
    'mark_by_splitted_text',
    'mark_with_sequence',
    'quick_count_holes',
    'single_file_pipeline',
    'restore_backup',
    
    # Sequence Builder
    'SequenceBuilder',
    'from_file_name',
    'from_splitted_text',

    # Operations
    'Operation',
    'AddMark',
    'AddCircle',
    'SubstituteCircle',
    'AddX',
    'RemoveCircle',
    'RemoveLayer',
    'PrintLayers',
    'Counter',
    'CountFiles',
    'CountHoles',
    'Aligner',
    
    # Manager
    'IterationManager',
    'iteration_manager',  # Alias legacy
    
    # Utils
    'BackupManager',
    'count_holes',
    'mult_campana',
    'find_all_circles',
    'find_circle_by_radius',
    
    # Checking
    'find_spec_holes',
    'find_circle_centers',
    'find_longer_entity',
    'print_document_layers',
    'print_entities',

    # DEPRECATED (manteinence to backward compatibility)
    'Conc',
    'FixSeq',
]



# ========== DEPRECATION WARNINGS ==========

def __getattr__(name):
    """
    Manages import of deprecated functions with warning.
    """
    import warnings
    
    deprecated = {
        'select_files': 'Use file_pattern in process_folder() instead',
        'iter_on_a_folder': 'Use Operation.process_folder() or IterationManager',
    }
    
    if name in deprecated:
        warnings.warn(
            f"{name} is deprecated. {deprecated[name]}",
            DeprecationWarning,
            stacklevel=2
        )
        raise AttributeError(f"Deprecated removed function: {name}")
    
    raise AttributeError(f"module 'snapmark' has no attribute '{name}'")