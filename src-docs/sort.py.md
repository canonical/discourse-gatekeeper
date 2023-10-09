<!-- markdownlint-disable -->

<a href="../src/sort.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `sort.py`
Sort items for publishing. 


---

<a href="../src/sort.py#L138"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `using_contents_index`

```python
using_contents_index(
    path_infos: Iterable[PathInfo],
    index_contents: Iterable[IndexContentsListItem],
    docs_path: Path
) → Iterator[PathInfo | IndexContentsListItem]
```

Sort PathInfos based on the contents index and alphabetical rank. 

Also updates the navlink title for any items matched to the contents index. 



**Args:**
 
 - <b>`path_infos`</b>:  Information about the local documentation files. 
 - <b>`index_contents`</b>:  The content index items used to apply sorting. 
 - <b>`docs_path`</b>:  The directory the documentation files are contained within. 



**Yields:**
 PathInfo sorted based on their location on the contents index and then by alphabetical rank. 


