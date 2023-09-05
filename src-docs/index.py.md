<!-- markdownlint-disable -->

<a href="../src/index.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `index.py`
Execute the uploading of documentation. 

**Global Variables**
---------------
- **DOC_FILE_EXTENSION**
- **DOCUMENTATION_FOLDER_NAME**
- **DOCUMENTATION_INDEX_FILENAME**
- **NAVIGATION_HEADING**
- **CONTENTS_HEADER**
- **CONTENTS_END_LINE_PREFIX**

---

<a href="../src/index.py#L55"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get`

```python
get(metadata: Metadata, base_path: Path, server_client: Discourse) → Index
```

Retrieve the local and server index information. 



**Args:**
 
 - <b>`metadata`</b>:  Information about the charm. 
 - <b>`base_path`</b>:  The base path to look for the metadata file in. 
 - <b>`server_client`</b>:  A client to the documentation server. 



**Returns:**
 The index page. 



**Raises:**
 
 - <b>`ServerError`</b>:  if interactions with the documentation server occurs. 


---

<a href="../src/index.py#L90"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../src/index.py#L205"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../src/index.py#L371"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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


