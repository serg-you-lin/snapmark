"""
core.py - Core components of SnapMark.

Contains IterationManager for multiple batch operations.
"""
import os
import ezdxf
from pathlib import Path
from snapmark.utils.helpers import find_dxf_files

try:
    from .utils.backup_manager import BackupManager
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False


class IterationManager:
    """
    Manages applying multiple operations in sequence on DXF files.
    
    Example:
        >>> manager = IterationManager("folder_path")
        >>> manager.add_operation(AddMark(...), CountHoles(...))
        >>> manager.execute()
    """
    
    def __init__(self, folder_path, use_backup_system=True):
        """
        Initializes the IterationManager with the specified folder path and backup option.

        Args:
            folder_path (str): The path of the folder containing the DXF files.
            use_backup_system (bool): If True, uses .bak for backups (recommended).
        """
        self.folder_path = folder_path
        self.operation_list = []
        self.use_backup_system = use_backup_system and BACKUP_AVAILABLE
        
        if use_backup_system and not BACKUP_AVAILABLE:
            print("⚠ BackupManager not available")
    
    def add_operation(self, *operations):
        """Adds operations to the pipeline."""
        for op in operations:
            self.operation_list.append(op)
    
    def execute(self, file_pattern="*.dxf", recursive=False):
        """
        Executes all operations on the files in the specified folder.
        
        Args:
            file_pattern (str): Pattern to filter files (e.g., "F*.dxf").
            recursive (bool): If True, includes subfolders.
        
        Returns:
            dict: Statistics containing {'processed': int, 'modified': int, 'errors': list}.
        """
        if not self.operation_list:
            print("⚠ No operations added")
            return {'processed': 0, 'modified': 0, 'errors': []}
        
        dxf_files = find_dxf_files(self.folder_path, recursive)

        if self.use_backup_system:
            print("🔧 Backup mode active")
        
        # Process files
        stats = {'processed': 0, 'modified': 0, 'errors': []}
        
        for file_path in dxf_files:
            processed, saved = self._process_single_file(str(file_path))
            if processed:
                stats['processed'] += 1
            if saved:
                stats['modified'] += 1
            if not processed:
                stats['errors'].append(str(file_path))

        # Final messages
        self._final_messages()
        
        # Report
        print(f"\n✓ Processed: {stats['processed']}")
        print(f"✓ Modified: {stats['modified']}")
        if stats['errors']:
            print(f"❌ Errors: {len(stats['errors'])}")
        
        return stats
    
    def _process_single_file(self, file_path: str):
        """
        Applies operations to a single file.
        Catches ALL errors and prints ONE clear message.
        """
        file_name = os.path.basename(file_path)
        folder = os.path.dirname(file_path)
        
        # --- BACKUP ---
        if self.use_backup_system:
            try:
                BackupManager.ensure_original(file_path)
            except PermissionError:
                print(f"🔒 The file '{file_name}' is currently open in another application. Please close it and try again.")
                return False, False
            except Exception as e:
                print(f"❌ Backup error on '{file_name}': {str(e)}")
                return False, False

        # --- OPEN FILE ---
        try:
            doc = ezdxf.readfile(file_path)
        except PermissionError:
            print(f"🔒 The file '{file_name}' is currently open in another application. Please close it and try again.")
            return False, False
        except Exception as e:
            print(f"❌ Cannot open '{file_name}': {str(e)}")
            return False, False

        # --- APPLY OPERATIONS ---
        should_save = False
        for operation in self.operation_list:
            try:
                result = operation.execute(doc, folder, file_name)
                should_save = should_save or result
                operation.message(file_name)
            except Exception as e:
                print(f"❌ Error processing '{file_name}': {str(e)}")
                return False, False  # processed=False, saved=False

        # --- SAVE ---
        if should_save:
            try:
                doc.saveas(file_path)
                return True, True   # processed=True, saved=True
            except PermissionError:
                ...
                return True, False  # processed=True, saved=False
            except Exception as e:
                ...
                return True, False

        return True, False          # processed=True, saved=False
    
    
    def _final_messages(self):
        """Prints final messages (e.g., from Counter)."""
        try:
            from .operations.counter import Counter
            for operation in self.operation_list:
                if isinstance(operation, Counter):
                    operation.count_message()
        except ImportError:
            pass
    
    def file_selection_logic(self, filter_files=None):
        """DEPRECATED: Use execute() instead."""
        import warnings
        warnings.warn(
            "file_selection_logic() is deprecated. Use execute().",
            DeprecationWarning,
            stacklevel=2
        )
        
        pattern = "*.dxf"
        if filter_files:
            if isinstance(filter_files, str):
                pattern = filter_files
            elif isinstance(filter_files, list) and filter_files:
                pattern = filter_files[0]
        
        return self.execute(file_pattern=pattern, recursive=False)


# Alias for backward compatibility with old scripts
iteration_manager = IterationManager