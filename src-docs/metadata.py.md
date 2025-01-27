<!-- markdownlint-disable -->

<a href="../src/gatekeeper/metadata.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `metadata.py`
Module for parsing metadata.yaml file. 

**Global Variables**
---------------
- **CHARMCRAFT_FILENAME**
- **CHARMCRAFT_NAME_KEY**
- **CHARMCRAFT_LINKS_KEY**
- **CHARMCRAFT_LINKS_DOCS_KEY**
- **METADATA_DOCS_KEY**
- **METADATA_FILENAME**
- **METADATA_NAME_KEY**

---

<a href="../src/gatekeeper/metadata.py#L22"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get`

```python
get(path: Path) → Metadata
```

Check for and read the metadata. 

The charm metadata can be in the file metadata.yaml or in charmcraft.yaml. From charmcraft version 2.5, the information should be in charmcraft.yaml, and the user should only modify that file. This function does not consider the case in which the name is in one file and the doc link is in the other. 



**Args:**
 
 - <b>`path`</b>:  The base path to look for the metadata files. 



**Returns:**
 The contents of the metadata file. 



**Raises:**
 
 - <b>`InputError`</b>:  if the metadata file does not exist or is malformed. 


