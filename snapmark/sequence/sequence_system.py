"""
Sequence system for SnapMark - Hybrid version.

Maintains Conc for compatibility, introduces SequenceBuilder as the main API.
"""

from email.mime import base
import os
from typing import List, Callable
from abc import ABC, abstractmethod


# ========== BASE INTERFACE ==========

class Sequence(ABC):
    """Base interface for all sequence types."""
    
    @abstractmethod
    def get_sequence_text(self, folder: str, file_name: str) -> str:
        """Generates the sequence text based on the provided folder and file name."""
        pass


# ========== NEW SYSTEM: COMPONENTS ==========

class SequenceComponent(ABC):
    """Base component - a piece of the sequence."""
    
    @abstractmethod
    def extract(self, folder: str, file_name: str) -> str:
        """Extracts the relevant text based on the provided folder and file name."""
        pass


class LiteralComponent(SequenceComponent):
    """Represents fixed text in the sequence."""

    def __init__(self, text: str):
        """
        Initializes the LiteralComponent with the specified text.

        Args:
            text (str): The fixed text to be included in the sequence.
        """

        self.text = text
    
    def extract(self, folder: str, file_name: str) -> str:
        """Returns the fixed text."""
        return self.text


class FileNameComponent(SequenceComponent):
    """Represents the file name without extension."""

    def __init__(self, trim_start: int = 0, trim_end: int = 0):
        """
        Initializes the FileNameComponent with optional trimming parameters.

        Args:
            trim_start (int): Number of characters to trim from the start of the file name.
            trim_end (int): Number of characters to trim from the end of the file name.
        """
        self.trim_start = trim_start
        self.trim_end = trim_end
        
    def extract(self, folder: str, file_name: str) -> str:
        base = os.path.splitext(file_name)[0]

        if self.trim_start < 0 or self.trim_end < 0:
            raise ValueError("trim values must be >= 0")

        if self.trim_start + self.trim_end >= len(base):
            return base  
        
        start = self.trim_start
        end = None if self.trim_end == 0 else -self.trim_end

        return base[start:end]

class FolderNameComponent(SequenceComponent):
    """Represents the folder name (optionally the first N characters)."""

    def __init__(self, num_chars: int = None, level: int = 0):
        """
        Initializes the FolderNameComponent with an optional character limit and level.

        Args:
            num_chars (int, optional): The number of characters to return from the folder name.
            level (int, optional): Folder level relative to the file (default 0 = immediate parent).
                                   0: parent folder (drawings)
                                   1: grandparent folder (LOT2024A)
                                   2: great-grandparent folder (Batches)
        """
        self.num_chars = num_chars
        self.level = level
    
    def extract(self, folder: str, file_name: str) -> str:
        """Returns the folder name at the specified level."""
        # Normalize path
        normalized = os.path.normpath(folder)
        parts = normalized.split(os.sep)
        
        # Remove empty parts
        parts = [p for p in parts if p]
        
        # Compute index from end: -1 (parent), grandparent, and so on.
        target_index = -(self.level + 1)
        
        if abs(target_index) > len(parts):
            raise ValueError(f"Level {self.level} too deep for path: {folder}")
        
        folder_name = parts[target_index]
        
        if self.num_chars:
            return folder_name[:self.num_chars]
        return folder_name
    

import os

class FilePartComponent(SequenceComponent):
    """Represents a specific part of the file name split by a separator."""

    def __init__(self, separator: str = "_", part_index: int = 0,
                 trim_start: int = 0, trim_end: int = 0):
        """
        Args:
            separator (str): Character used to split file name.
            part_index (int): Index of the split part to return.
            trim_start (int): Characters to remove from start of selected part.
            trim_end (int): Characters to remove from end of selected part.
        """
        self.separator = separator
        self.part_index = part_index
        self.trim_start = trim_start
        self.trim_end = trim_end

    def extract(self, folder: str, file_name: str) -> str:
        # 1. remove extension
        base = os.path.splitext(file_name)[0]

        # 2. split
        parts = base.split(self.separator)

        if self.part_index >= len(parts):
            raise ValueError(
                f"part_index {self.part_index} out of range for file: {file_name}"
            )

        value = parts[self.part_index]

        # 3. safety check trim
        if self.trim_start < 0 or self.trim_end < 0:
            raise ValueError("trim values must be >= 0")

        # 4. apply trim (IDENTICAL LOGIC STYLE to FileNameComponent)
        if self.trim_start + self.trim_end >= len(value):
            return value

        start = self.trim_start
        end = None if self.trim_end == 0 else -self.trim_end

        return value[start:end]


class CustomComponent(SequenceComponent):
    """Represents a custom component with a user-defined function."""

    def __init__(self, func: Callable[[str, str], str]):
        """
        Initializes the CustomComponent with a specified function.

        Args:
            func (Callable[[str, str], str]): A function that takes a folder and file name and returns a string.
        """

        self.func = func
    
    def extract(self, folder: str, file_name: str) -> str:
        """Returns the result of the custom function applied to the folder and file name."""

        return self.func(folder, file_name)


# ========== BUILDER ==========

class SequenceBuilder:
    """
    Builds sequences in a readable and composable manner.

    Examples:
        # Simple file name
        seq = SequenceBuilder().file_name().build()
        
        # File name + folder
        seq = (SequenceBuilder()
               .file_name()
               .folder(num_chars=2)
               .build())
        
        # First part of the name (split on '_')
        seq = (SequenceBuilder()
               .file_part(separator='_', part_index=0)
               .build())
    """
    
    def __init__(self):
        """Initializes the SequenceBuilder with an empty list of components and a default separator."""

        self.components: List[SequenceComponent] = []
        self.separator = "-"
    
    def literal(self, text: str) -> 'SequenceBuilder':
        """Adds fixed text to the sequence."""
        self.components.append(LiteralComponent(text))
        return self
    
    def file_name(self, trim_start: int = 0, trim_end: int = 0) -> 'SequenceBuilder':
        """Adds the file name (optionally trimming start/end characters)."""
        self.components.append(FileNameComponent(trim_start, trim_end))
        return self
    
    
    def folder(self, num_chars: int = None, level: int = 0) -> 'SequenceBuilder':
        """
        Adds the folder name to the sequence.
        
        Args:
            num_chars (int, optional): If specified, takes only the first N characters of the folder name.
            level (int, optional): Folder level relative to the file (default 0 = immediate parent).
                                0: immediate parent folder
                                1: grandparent folder  
                                2: great-grandparent folder
        
        Examples:
            Given path: /Batches/LOT2024A/drawings/part.dxf
            
            .folder()                      → "drawings"
            .folder(num_chars=4)           → "draw"
            .folder(level=1)               → "LOT2024A"
            .folder(level=1, num_chars=4)  → "LOT2"
        """
        self.components.append(FolderNameComponent(num_chars, level))
        return self


    def file_part(self, separator: str = '_', part_index: int = 0, trim_start: int = 0, trim_end: int = 0) -> 'SequenceBuilder':
        """
        Adds a part of the file name after splitting it.
        
        Example:
            File: "PART_123_A_5mm.dxf"
            - part_index=0 → "PART"
            - part_index=1 → "123"
            - part_index=2 → "A"
        
        Args:
            separator (str): The character used to separate parts (default is '_').
            part_index (int): The index of the part to extract (default is 0).
            trim_start (int): Number of characters to trim from the start of the part.
            trim_end (int): Number of characters to trim from the end of the part.
        """

        self.components.append(FilePartComponent(separator, part_index, trim_start, trim_end))
        return self
    
    def custom(self, func: Callable[[str, str], str]) -> 'SequenceBuilder':
        """Adds a custom component with a user-defined function."""

        self.components.append(CustomComponent(func))
        return self
    
    def set_separator(self, sep: str) -> 'SequenceBuilder':
        """
        Sets the separator between components (default is '-').
        
        Args:
            sep (str): The separator to use between components.
        """

        self.separator = sep
        return self
    
    def build(self) -> 'ComposedSequence':
        """Constructs the final sequence."""
        return ComposedSequence(self.components, self.separator)


# ========== COMPOSED SEQUENCE ==========

class ComposedSequence(Sequence):
    """A sequence composed of multiple components."""
    
    def __init__(self, components: List[SequenceComponent], separator: str = "-"):
        """
        Initializes the ComposedSequence with the specified components and separator.

        Args:
            components (List[SequenceComponent]): A list of components that make up the sequence.
            separator (str): The separator to use between components (default is "-").
        """

        self.components = components
        self.separator = separator
    
    def get_sequence_text(self, folder: str, file_name: str) -> str:
        """
        Generates the sequence text based on the provided folder and file name.

        Args:
            folder (str): The folder path where the file is located.
            file_name (str): The name of the file.

        Returns:
            str: The constructed sequence text in uppercase.
        """

        parts = [comp.extract(folder, file_name) for comp in self.components]
        
        parts = [p for p in parts if p]
        result = self.separator.join(parts)
        return result.upper()


# ========== COMMON SHORTCUTS ==========

def from_file_name(trim_start: int = 0, trim_end: int = 0) -> ComposedSequence:
    """Shortcut: sequence with only the file name, optionally trimmed."""
    return SequenceBuilder().file_name(trim_start=trim_start, trim_end=trim_end).build()


def from_splitted_text(separator: str = '_', part_index: int = 0, trim_start: int = 0, trim_end: int = 0) -> ComposedSequence:
    """Shortcut: first part of the filename based on a separator."""
    return SequenceBuilder().file_part(separator, part_index, trim_start, trim_end).build()


def from_literal(text: str) -> ComposedSequence:
    """Shortcut: fixed text component."""
    return SequenceBuilder().literal(text).build()



# ========== TEXT BUILDER ==========

class TextLine(ABC):
    """Base component - una riga di testo."""

    @abstractmethod
    def resolve(self, folder: str, file_name: str) -> str:
        pass


class StaticLine(TextLine):
    """Riga di testo fissa."""

    def __init__(self, text: str):
        self.text = text

    def resolve(self, folder: str, file_name: str) -> str:
        return self.text


class DynamicLine(TextLine):
    """Riga di testo dinamica, calcolata da una funzione."""

    def __init__(self, func: Callable[[str, str], str]):
        self.func = func

    def resolve(self, folder: str, file_name: str) -> str:
        return self.func(folder, file_name)


class ComposedText:
    """
    Lista di righe di testo composta da componenti statici e dinamici.
    Prodotta da TextBuilder.build() — analoga a ComposedSequence per AddMark.
    """

    def __init__(self, lines: List[TextLine]):
        self.lines = lines

    def get_lines(self, folder: str, file_name: str) -> List[str]:
        """Risolve tutte le righe per il file corrente."""
        return [line.resolve(folder, file_name) for line in self.lines]


class TextBuilder:
    """
    Costruisce liste di righe di testo in modo componibile.
    Speculare a SequenceBuilder, ma produce List[str] invece di str.

    Analogia: SequenceBuilder assembla una stringa per AddMark,
              TextBuilder assembla una lista di righe per AddText.

    Esempi:
        # Righe statiche
        tb = TextBuilder().static("REV:1").static("NOTE:OK").build()

        # Righe dinamiche dal filename
        tb = (TextBuilder()
              .line(lambda folder, f: f"Mat:{parse(f)['material']}")
              .line(lambda folder, f: f"Sp:{parse(f)['thickness']}")
              .build())

        # Mix con normalizzazione esterna
        material_map = {"S235": "FE-DECAPATO"}
        tb = (TextBuilder()
              .line(lambda folder, f: f"Mat:{material_map.get(parse(f)['material'], parse(f)['material'])}")
              .static("REV:1")
              .build())
    """

    def __init__(self):
        self._lines: List[TextLine] = []

    def static(self, text: str) -> 'TextBuilder':
        """Aggiunge una riga fissa."""
        self._lines.append(StaticLine(text))
        return self

    def line(self, func: Callable[[str, str], str]) -> 'TextBuilder':
        """
        Aggiunge una riga dinamica.

        Args:
            func: funzione (folder, file_name) -> str
        """
        self._lines.append(DynamicLine(func))
        return self

    def build(self) -> ComposedText:
        """Congela il builder e restituisce un ComposedText pronto all'uso."""
        if not self._lines:
            raise ValueError("TextBuilder: nessuna riga definita. Aggiungi almeno .static() o .line().")
        return ComposedText(list(self._lines))



# ========== OLD SYSTEM (DEPRECATED) ==========

class Conc(Sequence):
    """
    DEPRECATED: Use SequenceBuilder instead.
    
    Mantein for compatibility with existent code.
    Will be removed in 3.0.0 version.
    """
    
    FIRST_FOLDER_CHAR = '[FDFC]'
    FOLDER_NAME = '[FDN]'
    LAST_FILE_CHAR_IF_LETTER = '[LIL]'
    FILE_NAME = '[FLN]'
    FILE_NAME_CAMPANA = '[FLC]'
    PART_NUMBER_CAMPANA = '[PNC]'
    LETTERA_DIVERSA_OGNI_NOME = '[LDON]'
    OEP_FILE_NAME = '[OEPFN]'
    
    def __init__(self, *text):
        self.text = text
        self.number = 1
    
    def num_char(self, number=1):
        self.number = number
        return self
    
    def get_sequence_text(self, folder: str, file_name: str) -> str:
        text_list = []
        for t in self.text:
            if t == Conc.FIRST_FOLDER_CHAR:
                folder_name = os.path.basename(os.path.normpath(folder))
                first_char_folder = folder_name[:self.number]
                text_list.append(first_char_folder)
            
            elif t == Conc.FILE_NAME:
                last_dot = file_name.rfind('.')
                text_list.append(file_name[:last_dot])
            
            elif t == Conc.FILE_NAME_CAMPANA:
                first_underscore = file_name.find('_')
                text_list.append(file_name[:first_underscore])
            
            elif t == Conc.PART_NUMBER_CAMPANA:
                first_underscore = file_name.find("_")
                second_underscore = file_name.find("_", first_underscore + 1)
                name = file_name[first_underscore:second_underscore]
                text_list.append(name)
            
            elif t == Conc.LAST_FILE_CHAR_IF_LETTER:
                first_underscore = file_name.find('_')
                if first_underscore > 0:
                    last_char = file_name[first_underscore - 1]
                    if last_char.isalpha():
                        text_list.append(last_char)
            
            else:
                text_list.append(t)
        
        return '-'.join(text_list)


class FixSeq(Sequence):
    """Sequenza con testo fisso. DEPRECATO: usa from_literal() invece."""
    def __init__(self, text: str):
        self.text = text
    
    def get_sequence_text(self, folder: str, file_name: str) -> str:
        return self.text

