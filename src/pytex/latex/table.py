"""Generate a latex table output."""

from abc import ABC, abstractmethod
import itertools
import numbers
from typing import Union

from pathlib import Path

import numpy as np


def _make_text_latex_save(text: str) -> str:
    # check sub and super script
    text = text.replace("_", r"\_").replace("^", r"\^")

    # check math mode
    text = text.replace("$", r"\$")
    text = text.replace(r"\(", "(").replace(r"\)", ")")
    text = text.replace(r"\[", "[").replace(r"\]", "]")

    # TODO: check for commands?

    return text

def _lengths(data):
    return np.array([len(el) for el in data], dtype=int)


class _tableElement(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def to_latex(self) -> str:
        pass


class _tableSeparator(_tableElement):
    def __init__(self):
        pass

    def to_latex(self) -> str:
        return "\\midrule"


class _tableRow(_tableElement):
    def __init__(self, data: list, parent: "Table"):
        super().__init__()

        self._parent_table = parent
        self._cell_data = list(map(self.parent._parse_cell_data, data))
        self._cell_sizes = _lengths(self._cell_data)

    @property
    def cell_sizes(self):
        return self._cell_sizes

    @property
    def cell_data(self):
        return self._cell_data

    @property
    def parent(self):
        return self._parent_table

    @property
    def table_cell_separator(self):
        return " & "

    @property
    def table_row_end(self):
        return " \\\\"

    def to_latex(self) -> str:
        result = ""
        # Convert a valid line into a table body
        for idx, element in enumerate(self.cell_data):
            result += element.ljust(self.parent._cell_widths[idx])

            if idx < self._parent_table.cols - 1:
                result += self.table_cell_separator

        result += self.table_row_end

        return result

class _tableMultiColumn(_tableRow):
    def __init__(
        self,
        parent: "Table",
        num_cols: int,
        align: str,
        multi_col_data,
        other_data: list,
    ):
        super().__init__(parent=parent, data=other_data)

        self._num_cols = num_cols
        self._align = align

        self._multicol_data = self.parent._parse_cell_data(multi_col_data)

    def to_latex(self) -> str:
        needed_space = sum(self._parent_table._cell_widths[: self._num_cols])
        needed_space += len(self.table_cell_separator) * (self._num_cols - 1)
        result = f"\\multicolumn{{{self._num_cols}}}{{{self._align}}}{{{self._multicol_data}}}".ljust(needed_space)

        for idx, element in enumerate(self.cell_data):
            result += self.table_cell_separator
            result += element.ljust(self.parent._cell_widths[idx + self._num_cols])

        result += self.table_row_end

        return result


class Table:
    """Encapsulates a latex table."""

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
        self._data: list[_tableElement] = []
        self._cell_widths = _lengths(self._headers)
        self._scale = scale

        self._number_precision = 3

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
        return len(self._data)

    @property
    def headers(self):
        """The headers of the table."""
        return self._headers

    @property
    def caption(self):
        """The caption of the table."""
        return self._caption if self._caption else "Here goes my caption."

    @property
    def layout(self) -> str:
        """The layout of the table."""
        return "".join(self._layout)

    @property
    def scale(self) -> float:
        """A scale factor for the table width."""
        return self._scale

    @property
    def number_precision(self) -> int:
        return self._number_precision

    @number_precision.setter
    def number_precision(self, value: int):
        self._number_precision = value

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
        cleaned_string = "".join(itertools.chain(*layout_string.split()))
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
        """Add a separator to the table."""
        self._data.append(_tableSeparator())

    def add_multi_column(
        self,
        multicol_data,
        num_cols: Union[int, None] = None,
        align: str = "c",
        other_data: Union[list, None] = None,
    ) -> None:
        # clean up some of the inputs so we can do proper checking
        num_other_cells = 0 if other_data is None else len(other_data)
        num_cols = self.cols if num_cols is None else num_cols

        if other_data is None:
            other_data = []

        assert num_cols + num_other_cells == self.cols, \
            "Provided data count does not match available cells in table!"

        self._data.append(
            _tableMultiColumn(self,
                              num_cols,
                              align,
                              multicol_data,
                              other_data)
        )

    def add_row(self, row_data: list) -> None:
        """Add a row.

        Valid input is any list containing at least self.cols elements.
        The list will be stringified using str(...).

        Args:
            row_data (_type_): The data of the row
        """
        # ensure that we have sufficient elements
        # TODO: what if previous is multi-row?
        assert len(row_data) >= self.cols, \
            "Cannot match given row data to available cells!"

        new_row = _tableRow(row_data, parent=self)

        self._cell_widths = np.max(
            [self._cell_widths, new_row.cell_sizes], axis=0)
        self._data.append(new_row)

    def _parse_cell_data(self, data) -> str:
        """Parse the content of a single cell element to a string.

        Args:
            data (_type_): Any form of data that should be displayed in a cell.

        Returns:
            str: A (latex-suited) stringified version.
        """
        # TODO: do some more sophisticated parsing

        # wrap numbers in SI-package numbers
        if isinstance(data, numbers.Number):
            return f"\\num{{{data:.{self.number_precision}f}}}"

        # default - convert it to string and make it save
        return _make_text_latex_save(str(data))

    # TODO: technically, the header is just the first row in the table, maybe we can use that?
    def _generate_header(self) -> str:
        """Generate a latex header string."""
        result = "\t\t"
        for idx, header in enumerate(self.headers):
            result += header.ljust(self._cell_widths[idx])

            if idx < self.cols - 1:
                result += " & "

        result += " \\\\"

        return result

    def _line_to_table_body(self, line: _tableElement) -> str:
        """Generate a single latex table row for a given data entry.
        If None is given, a separator is inserted.
        """
        return "\t\t" + line.to_latex()

    def _generate_table_body(self) -> list[str]:
        """Generate the table body (i.e., the cell data of the table)."""
        return [self._line_to_table_body(line) for line in self._data]

    def _generate_latex(self) -> list[str]:
        """Generate the latex table.

        Returns:
            list[str]: A list containing each line as a string-representation of the table.
        """
        content = (
            [
                "\\begin{table}[h]",
                "\t\\centering",
                f"\t\\caption{{{self.caption}}}",
                f"\t\\label{{tbl:{self.caption.split()[0].lower()}}}",
                f"\t\\begin{{tabularx}}{{{self.scale}\\linewidth}}{{{self.layout}}}",
                "\t\t\\toprule",
                self._generate_header(),
                "\t\t\\midrule",
            ]
            + self._generate_table_body()
            + ["\t\t\\bottomrule", "\t\\end{tabularx}", "\\end{table}"]
        )

        return content

    def save(self, file_path: Path):
        """Save the table to a file.

        Args:
            file_path (Path): The save file destination.
        """
        content = self._generate_latex()

        with open(file_path, "wt", encoding="utf-8") as file:
            file.writelines("\n".join(content))
