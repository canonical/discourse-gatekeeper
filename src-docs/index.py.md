<!-- markdownlint-disable -->

<a href="../src/gatekeeper/index.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `index.py`
Execute the uploading of documentation. 

**Global Variables**
---------------
- **DOC_FILE_EXTENSION**
- **DOCUMENTATION_INDEX_FILENAME**
- **NAVIGATION_HEADING**
- **CONTENTS_HEADER**
- **CONTENTS_END_LINE_PREFIX**

---

<a href="../src/gatekeeper/index.py#L54"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get`

```python
get(metadata: Metadata, docs_path: Path, server_client: Discourse) → Index
```

Retrieve the local and server index information. 



**Args:**
 
 - <b>`metadata`</b>:  Information about the charm. 
 - <b>`docs_path`</b>:  The base path to look for the documentation. 
 - <b>`server_client`</b>:  A client to the documentation server. 



**Returns:**
 The index page. 



**Raises:**
 
 - <b>`ServerError`</b>:  if interactions with the documentation server occurs. 


---

<a href="../src/gatekeeper/index.py#L89"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `contents_from_page`

```python
contents_from_page(page: str) → str
```

Get index file contents from server page. 



**Args:**
 
 - <b>`page`</b>:  Page contents from server. 



**Returns:**
 Index file contents. 


---

<a href="../src/gatekeeper/index.py#L204"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_content_for_server`

```python
get_content_for_server(index_file: IndexFile) → str
```

Get the contents from the index file that should be passed to the server. 



**Args:**
 
 - <b>`index_file`</b>:  Information about the local index file. 



**Returns:**
 The contents of the index file that should be stored on the server. 


---

<a href="../src/gatekeeper/index.py#L261"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `classify_item_reference`

```python
classify_item_reference(
    reference: str,
    docs_path: Path
) → <enum 'ItemReferenceType'>
```

Classify the type of a reference. 



**Args:**
 
 - <b>`reference`</b>:  The reference to classify. 
 - <b>`docs_path`</b>:  The parent path of the reference. 



**Returns:**
 The type of the reference. 


---

<a href="../src/gatekeeper/index.py#L413"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_contents`

```python
get_contents(
    index_file: IndexFile,
    docs_path: Path
) → Iterator[IndexContentsListItem]
```

Get the contents list items from the index file. 



**Args:**
 
 - <b>`index_file`</b>:  The index file to read the contents from. 
 - <b>`docs_path`</b>:  The base directory of all items. 



**Returns:**
 Iterator with all items from the contents list. 


---

## <kbd>class</kbd> `ItemReferenceType`
Classification for the path of an item. 

Attrs:  EXTERNAL: a link to an external resource.  DIR: a link to a local directory.  FILE: a link to a local file.  UNKNOWN: The reference is not a known type. 





