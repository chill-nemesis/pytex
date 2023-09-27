"""Generate a latex table output."""

import itertools
from typing import Union

from pathlib import Path

import numpy as np


def _lengths(data):
    return np.array([len(el) for el in data], dtype=int)


class Table:
    """Encapsulates a latex table.
    """

    def __init__(self,
                 header: list[str],
                 caption: Union[str, None] = None,
                 scale: float = 1,
                 layout: Union[str, None] = None):
        """Create a new latex table.

        Args:
            header (list[str]): The header of the table. This cannot be changed later and 
            defines the total number of columns of the table! 
            caption (Union[str, None], optional): The caption of the table. 
            If no caption is set, a default text is generated. Defaults to None.
            scale (float, optional): A scaling factor to apply to the table. Defaults to 1.
            layout (Union[str, None], optional): The layout of the table columns. If not set, all 
            columns will default to a left-justified cell. Defaults to None.
        """
        self._headers = header
        self._caption = caption
        self._data: list[list[str]] = []
        self._column_widths = _lengths(self._headers)
        self._scale = scale

        if layout is None:
            self._layout = np.array(["l"] * self.cols, dtype=str)
        else:
            self.set_layout(layout)

    @property
    def cols(self):
        """Total number of columns. This cannot change."""
        return len(self.headers)

    @property
    def rows(self):
        """Total number of rows."""
        return len(self.data)

    @property
    def headers(self):
        """The headers of the table."""
        return self._headers

    @property
    def caption(self):
        """The caption of the table."""
        return self._caption if self._caption else "Here goes my caption."

    @property
    def data(self) -> list[list[str]]:
        """The table body. 
        Each list represents one row, and each list per row represents the cell data.
        A separator is marked by a None-entry."""
        return self._data

    @property
    def layout(self) -> str:
        """The layout of the table.
        """
        return ''.join(self._layout)

    @property
    def scale(self) -> float:
        """A scale factor for the table width."""
        return self._scale

    def set_layout(self, layout_string: str, idx=None):
        """Set the layout of the table.
        Input can either be a string and a start index 
        (i.e., set the layout of a specific column/starting from a given column)
        or the complete layout string (idx == None).

        Note: This method does not check for layout-token validity!

        Args:
            layout_string (str): The layout for the table or one of its columns.
            idx (_type_, optional): Index for modifying a single column layout. 
            If None, the given layout string is assumed to be used for the entire table and must
            provide sufficient layout tokens. Defaults to None.

        Raises:
            IndexError: _description_
        """
        cleaned_string = ''.join(itertools.chain(*layout_string.split()))
        if idx is None:
            assert len(cleaned_string) >= self.cols, \
                "Not enough layout identifiers provided!"

            self._layout = np.array(list(cleaned_string[:self.cols]),
                                    dtype=str)
            return

        if idx >= self.cols:
            raise IndexError("Index is out of bounds!")

        self._layout[idx] = cleaned_string

    def add_separator(self) -> None:
        self._data.append(None)

    def add_row(self, row_data) -> None:
        """Add a row.

        Valid input is any list containing at least self.cols elements.
        The list will be stringified using str(...).

        Args:
            row_data (_type_): The data of the row
        """
        # ensure that we have sufficient elements
        assert len(row_data) >= self.cols, \
            "Cannot match given row data to available cells!"

        # TODO: we can do some more sophisticated parsing here
        new_data = list(map(str, row_data))

        self._column_widths = np.max([self._column_widths,
                                     _lengths(new_data)],
                                     axis=0)
        self._data.append(new_data)

    def _generate_header(self) -> str:
        """Generate a latex header string.
        """
        result = "\t\t"
        for idx, header in enumerate(self.headers):
            result += header.ljust(self._column_widths[idx])

            if idx < self.cols - 1:
                result += " & "

        result += " \\\\"

        return result

    def _line_to_table_body(self, line: Union[None, list[str]]) -> str:
        """Generate a single latex table row for a given data entry.
        If None is given, a separator is inserted.
        """
        result = "\t\t"

        # Special case, insert a separator
        if line is None:
            return result + "\\midrule"

        # Convert a valid line into a table body
        for idx, element in enumerate(line):
            result += element.ljust(self._column_widths[idx])

            if idx < self.cols - 1:
                result += " & "

        result += " \\\\"

        return result

    def _generate_table_body(self) -> list[str]:
        """Generate the table body (i.e., the cell data of the table).
        """
        return [self._line_to_table_body(line) for line in self.data]

    def _generate_latex(self) -> list[str]:
        """Generate the latex table.

        Returns:
            list[str]: A list containing each line as a string-representation of the table.
        """
        content = [
            "\\begin{table}[h]",
            "\t\\centering",
            f"\t\\caption{{{self.caption}}}",
            f"\t\\label{{tbl:{self.caption.split()[0].lower()}}}",
            f"\t\\begin{{tabularx}}{{{self.scale}\\linewidth}}{{{self.layout}}}",
            "\t\t\\toprule",
            self._generate_header(),
            "\t\t\\midrule"] \
            + self._generate_table_body() + [
            "\t\t\\bottomrule",
            "\t\\end{tabularx}",
            "\\end{table}"
        ]

        return content

    def save(self, file_path: Path):
        """Save the table to a file.

        Args:
            file_path (Path): The save file destination.
        """
        content = self._generate_latex()

        with open(file_path, "wt", encoding="utf-8") as file:
            file.writelines('\n'.join(content))
