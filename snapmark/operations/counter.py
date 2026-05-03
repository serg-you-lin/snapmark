"""
Counter Operations Module - Updated for Phase 2.

"""
from snapmark.operations.basic_operations import Operation


class Counter(Operation):
    """Base class for counting operations."""
    
    def __init__(self):
        """Initializes the Counter with a counter set to zero and processing flags."""
        super().__init__()
        self.counter = 0
        self.create_new = False 
        self.is_processing_folder = False
        self.modifies_files = False  
    
    def execute(self, doc, folder, file_name):
        """Abstract method to be implemented in subclasses."""
        pass
    
    def message(self, file_name):
        """Optional message for a single file."""
        pass
    
    def add_to_counter(self, quantity):
        """Increments the counter by the specified quantity."""
        self.counter += quantity
    
    def count_message(self):
        """Final message with the total count. To be implemented in subclasses."""
        pass
    
    def execute_single(self, file_path: str, use_backup: bool = False, print_message: bool = True) -> bool:
        """
        Executes the counting operation on a single file.
        
        NOTE: Counter never modifies files, so use_backup is ignored.
        
        Returns:
            bool: Always returns False since Counter does not modify files.
        """
        # Counter do not modify files, so ignore use_backup
        result = super().execute_single(file_path, use_backup=False)
        
        if print_message and not self.is_processing_folder:
            self.count_message()
        
        return False  
    
    @classmethod
    def process_folder(cls, folder_path: str, operation_instance: 'Counter',
                      use_backup: bool = False, recursive: bool = False,
                      file_pattern: str = "*.dxf") -> dict:
        """
        Overrides for Counter: does not use backup (does not modify files) 
        and adds count_message() at the end.
        
        Args:
            folder_path: Path of the folder.
            operation_instance: Instance of the Counter operation to apply.
            use_backup: If True, creates backups (ignored for Counter).
            recursive: If True, processes subfolders as well.
            file_pattern: Pattern to filter files (default: "*.dxf").
            
        Returns:
            dict: Statistics containing {'processed': int, 'modified': int, 'errors': list}.
        """

        operation_instance.is_processing_folder = True

        # Force use_backup=False for Counter (does not modify files)
        stats = super(Counter, cls).process_folder(
            folder_path, operation_instance, 
            use_backup=False,  # Counter non modifica mai
            recursive=recursive, 
            file_pattern=file_pattern
        )
        
        # Final message with total count
        operation_instance.count_message()
        stats['total_count'] = operation_instance.counter
        
        return stats


class CountFiles(Counter):
    """Counts how many DXF files are present in the folder."""
    
    def __init__(self):
        """Initializes the CountFiles operation."""
        super().__init__()
    
    def execute(self, doc, folder, file_name):
        """Increments the counter by 1 for each file."""
        self.add_to_counter(1)
        return False  # Non modifica il file
    
    def message(self, file_name):
        """Optional message for a single file (usually silent)."""
        pass
    
    def count_message(self):
        """Final message with the total count."""
        print(f"✓ Total files in the folder: {self.counter}")


class CountHoles(Counter):
    """Counts holes (circles) in DXF files."""
    
    def __init__(self, find_circle_function, verbose=False):
        """
        Initializes the CountHoles operation with the specified parameters.

        Args:
            find_circle_function: Function that finds circles in the document.
                                  Example: find_circle_by_radius(min_diam=5, max_diam=10).
            verbose (bool): If True, prints a message for each file (default is False).
        """

        super().__init__()
        self.find_circle_function = find_circle_function
        self.verbose = verbose
        self.holes_count = None
        self.function = None  # For optional multiplier (see mult())
    
    def execute(self, doc, folder, file_name):
        """Counts holes in the file and adds to the total."""
        holes = self.find_circle_function(doc)
        
        if self.function:
            self.holes_count = count_holes(holes) * self.function(file_name)
        else:
            self.holes_count = count_holes(holes)
        
        self.add_to_counter(self.holes_count)
        return False  
    
    def message(self, file_name):
        """Optional message for a single file."""
        if self.verbose:
            if not self.holes_count or self.holes_count == 0:
                print(f"  {file_name}: no holes found")
            else:
                print(f"  {file_name}: {self.holes_count} holes found")
    
    def count_message(self):
        """Final message with the total count."""
        print(f"✓ Total holes: {self.counter}")
    
    def mult(self, function):
        """
        Applies a multiplier to the count (e.g., for quantity from file name).
        
        Args:
            function: A function that takes file_name and returns a number.
                      Example: mult_campana to extract quantity from file name.
        
        Returns:
            self (for method chaining).
        """

        self.function = function
        return self


# Helper function (if not already defined)
def count_holes(holes):
    """Conta il numero di fori."""
    return len(list(holes))


