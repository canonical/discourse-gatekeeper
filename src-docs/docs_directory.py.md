<!-- markdownlint-disable -->

<a href="../src/gatekeeper/docs_directory.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `docs_directory.py`
Class for reading the docs directory. 

**Global Variables**
---------------
- **DOC_FILE_EXTENSION**

---

<a href="../src/gatekeeper/docs_directory.py#L46"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `calculate_table_path`

```python
calculate_table_path(path_relative_to_docs: Path) → tuple[str, ]
```

Calculate the table path of a path. 



**Args:**
 
 - <b>`path_relative_to_docs`</b>:  The path to calculate the table path for relative to the docs  directory. 



**Returns:**
 The relative path to the docs directory, replacing / with -, removing the extension and converting to lower case. 


---

<a href="../src/gatekeeper/docs_directory.py#L128"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `read`

```python
read(docs_path: Path) → Iterator[PathInfo]
```

Read the docs directory and return information about each directory and documentation file. 

Algorithm:  1.  Get a list of all sub directories and .md files in the docs folder.  2.  For each directory/ file:  2.1. Calculate the level based on the number of sub-directories to the docs directory  including the docs directory.  2.2. Calculate the table path using the relative path to the docs directory, replacing  / with -, removing the extension and converting to lower case.  2.3. Calculate the navlink title based on the first heading, first line if there is no  heading or the file/ directory name excluding the extension with - replaced by  space and titlelized if the file is empty or it is a directory. 



**Args:**
 
 - <b>`docs_path`</b>:  The path to the docs directory containing all the documentation. 



**Returns:**
 Information about each directory and documentation file in the docs folder. 


---

<a href="../src/gatekeeper/docs_directory.py#L155"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `has_docs_directory`

```python
has_docs_directory(docs_path: Path) → bool
```

Return existence of docs directory from base path. 



**Args:**
 
 - <b>`docs_path`</b>:  Docs path of the repository where docs are 



**Returns:**
 True if documentation folder exists, False otherwise 


