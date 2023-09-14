<!-- markdownlint-disable -->

<a href="../src/action.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `action.py`
Module for taking the required actions to match the server state with the local state. 

**Global Variables**
---------------
- **DRY_RUN_NAVLINK_LINK**
- **DRY_RUN_REASON**
- **BASE_MISSING_REASON**
- **FAIL_NAVLINK_LINK**
- **NOT_DELETE_REASON**

---

<a href="../src/action.py#L459"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `run_all`

```python
run_all(
    actions: Iterable[CreatePageAction | CreateGroupAction | CreateExternalRefAction | NoopPageAction | NoopGroupAction | NoopExternalRefAction | UpdatePageAction | UpdateGroupAction | UpdateExternalRefAction | DeletePageAction | DeleteGroupAction | DeleteExternalRefAction],
    index: Index,
    discourse: Discourse,
    dry_run: bool,
    delete_pages: bool
) → tuple[str, list[ActionReport]]
```

Take the actions against the server. 



**Args:**
 
 - <b>`actions`</b>:  The actions to take. 
 - <b>`index`</b>:  Information about the index. 
 - <b>`discourse`</b>:  A client to the documentation server. 
 - <b>`dry_run`</b>:  If enabled, only log the action that would be taken. 
 - <b>`delete_pages`</b>:  Whether to delete pages that are no longer needed. 



**Returns:**
 A 2-element tuple with the index url and the reports of all the requested action. 


---

## <kbd>class</kbd> `UpdateCase`
The possible cases for the update action. 

Attrs:  DRY_RUN: Do not make any changes.  CONTENT_CHANGE: The content has been changed.  BASE_MISSING: The base content is not available.  DEFAULT: No other specific case applies. 





