<!-- markdownlint-disable -->

<a href="../src/metadata.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `metadata.py`
Module for parsing metadata.yaml file. 

**Global Variables**
---------------
- **METADATA_DOCS_KEY**
- **METADATA_FILENAME**
- **METADATA_NAME_KEY**

---

<a href="../src/metadata.py#L18"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get`

```python
get(path: Path) → Metadata
```

Check for and read the metadata. 



**Args:**
 
 - <b>`path`</b>:  The base path to look for the metadata file in. 



**Returns:**
 The contents of the metadata file. 



**Raises:**
 
 - <b>`InputError`</b>:  if the metadata file does not exists or is malformed. 


