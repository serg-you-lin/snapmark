import os

class Sequence:
    """Base class for creating sequences of text for marking."""
    def get_sequence_text(self, folder, file_name):
        """
        Retrieves the sequence text based on the provided folder and file name.

        Args:
            folder (str): The folder path where the file is located.
            file_name (str): The name of the file.

        Returns:
            str: The sequence text.

        Raises:
            Exception: If the sequence text has not been constructed.
        """

        if self.text == None:
            raise Exception('Build the sequence first.') 
        else:
            return self.text

    def prompt_seq(self):
        """Prompts the user to input the marking text."""
        self.text = input("Enter marking text: ")


class Conc(Sequence): 
    """Creates a sequence by concatenating various strings.""" 
    FIRST_FOLDER_CHAR = '[FDFC]'
    FOLDER_NAME ='[FDN]'
    LAST_FILE_CHAR_IF_LETTER = '[LIL]'
    FILE_NAME = '[FLN]'
    FILE_NAME_CAMPANA = '[FLC]'
    PART_NUMBER_CAMPANA = '[PNC]'
    LETTERA_DIVERSA_OGNI_NOME = '[LDON]'
    OEP_FILE_NAME = '[OEPFN]'

    def __init__(self, *text):
        """
        Initializes the Conc class with the specified text parts.

        Args:
            text: Variable length argument list of text parts to concatenate.
        """

        self.text = text
        self.number = 1
    
    def __sep_logic(file_name, sep):
        """Extracts the part of the file name before the specified separator."""
        separator = file_name.find(sep)
        name = file_name[:separator]
        return name

    def num_char(self, number=1):
        """
        Sets the number of characters to consider for the first folder name.

        Args:
            number (int): The number of characters (default is 1).

        Returns:
            self: For method chaining.
        """

        self.number = number

        return self 

    def get_sequence_text(self, folder, file_name):
        """
        Constructs the sequence text based on the specified folder and file name.

        Args:
            folder (str): The folder path where the file is located.
            file_name (str): The name of the file.

        Returns:
            str: The constructed sequence text in uppercase.
        """

        text_list = []
        for t in self.text:
            if t == Conc.FIRST_FOLDER_CHAR:
                folder_name = os.path.basename(os.path.normpath(folder))
                num = self.number
                first_char_folder = folder_name[:num]
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

            elif t == Conc.OEP_FILE_NAME:
                pass
                
            else:
                text_list.append(t)

        result = '-'.join(text_list)  
        return result.upper()  
        

class FixSeq(Sequence):
    """Class for fixed sequences."""

    def __init__(self, text):
        """
        Initializes the FixSeq class with the specified text.

        Args:
            text (str): The fixed sequence text.
        """
        self.text = text

class PromptSeq(Sequence):
    """Class for prompting the user to input a sequence."""
    
    def __init__(self):
        """Initializes the PromptSeq class and prompts for sequence text."""
        self.text = input("Insert sequence text: ")