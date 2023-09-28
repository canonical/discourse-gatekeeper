<!-- markdownlint-disable -->

<a href="../src/migration.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `migration.py`
Module for migrating remote documentation into local git repository. 

**Global Variables**
---------------
- **EMPTY_DIR_REASON**
- **GITKEEP_FILENAME**

---

<a href="../src/migration.py#L219"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `make_parent`

```python
make_parent(docs_path: Path, document_meta: MigrationFileMeta) → Path
```

Construct path leading to document to be created. 



**Args:**
 
 - <b>`docs_path`</b>:  Path to documentation directory. 
 - <b>`document_meta`</b>:  Information about document to be migrated. 



**Returns:**
 Full path to the parent directory of the document to be migrated. 


---

<a href="../src/migration.py#L371"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `run`

```python
run(
    table_rows: Iterable[TableRow],
    index_content: str,
    discourse: Discourse,
    docs_path: Path
) → None
```

Write table contents to the document directory. 



**Args:**
 
 - <b>`table_rows`</b>:  Iterable sequence of documentation structure to be migrated. 
 - <b>`index_content`</b>:  Main content describing the charm. 
 - <b>`discourse`</b>:  Client to the documentation server. 
 - <b>`docs_path`</b>:  The path to the docs directory containing all the documentation. 



**Raises:**
 
 - <b>`MigrationError`</b>:  if any migration report has failed. 


