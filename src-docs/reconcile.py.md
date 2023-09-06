<!-- markdownlint-disable -->

<a href="../src/reconcile.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `reconcile.py`
Module for calculating required changes based on docs directory and navigation table. 

**Global Variables**
---------------
- **DOCUMENTATION_TAG**
- **NAVIGATION_TABLE_START**

---

<a href="../src/reconcile.py#L389"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `run`

```python
run(
    sorted_path_infos: Iterable[PathInfo],
    table_rows: Iterable[TableRow],
    clients: Clients,
    base_path: Path
) → Iterator[CreateAction | NoopAction | UpdateAction | DeleteAction]
```

Reconcile differences between the docs directory and documentation server. 

Preserves the order of path_infos although does not for items only in table_rows. 

This function needs to match files and directories locally to items on the navigation table on the server knowing that there may be cases that are not matched. The navigation table relies on the order that items are displayed to figure out the hierarchy/ page grouping (this is not a design choice of this action but how the documentation is interpreted by charmhub). Assume the `path_infos` have been sorted to ensure that the hierarchy will be calculated correctly by the server when the new navigation table is generated. 

Items only in table_rows won't have their order preserved. Those items are the items that are only on the server, i.e., those keys will just result in delete actions which have no effect on the navigation table that is generated and hence ordering for them doesn't matter. 



**Args:**
 
 - <b>`base_path`</b>:  The base path of the repository. 
 - <b>`sorted_path_infos`</b>:  Information about the local documentation files. 
 - <b>`table_rows`</b>:  Rows from the navigation table. 
 - <b>`clients`</b>:  The clients to interact with things like discourse and the repository. 



**Returns:**
 The actions required to reconcile differences between the documentation server and local files. 


---

<a href="../src/reconcile.py#L436"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `index_page`

```python
index_page(
    index: Index,
    table_rows: Iterable[TableRow]
) → CreateIndexAction | NoopIndexAction | UpdateIndexAction
```

Reconcile differences for the index page. 



**Args:**
 
 - <b>`index`</b>:  Information about the index on the server and locally. 
 - <b>`table_rows`</b>:  The current navigation table rows based on local files. 



**Returns:**
 The action to take for the index page. 


