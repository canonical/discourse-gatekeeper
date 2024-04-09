<!-- markdownlint-disable -->

<a href="../src/gatekeeper/navigation_table.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `navigation_table.py`
Module for parsing and rendering a navigation table. 


---

<a href="../src/gatekeeper/navigation_table.py#L123"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `from_page`

```python
from_page(page: str, discourse: Discourse) → Iterator[TableRow]
```

Create an instance based on a markdown page. 

Algorithm:  1.  Extract the table based on a regular expression looking for a 3 column table with  the headers level, path and navlink (case insensitive). If the table is not found,  assume that it is equivalent to a table without rows.  2.  Process the rows line by line:  2.1. If the row matches the header or filler pattern, skip it.  2.2. Extract the level, path and navlink values. 



**Args:**
 
 - <b>`page`</b>:  The page to extract the rows from. 
 - <b>`discourse`</b>:  API to the Discourse server. 



**Returns:**
 The parsed rows from the table. 


---

<a href="../src/gatekeeper/navigation_table.py#L153"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `generate_table_row`

```python
generate_table_row(lines: Sequence[str]) → Iterator[TableRow]
```

Return an iterator with the TableRows representing the parsed table lines. 



**Args:**
 
 - <b>`lines`</b>:  list of strings representing the different lines. 



**Yields:**
 parsed TableRow object, representing the row of the table 


