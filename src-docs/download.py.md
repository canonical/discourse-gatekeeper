<!-- markdownlint-disable -->

<a href="../src/download.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `download.py`
Library for downloading docs folder from charmhub. 

**Global Variables**
---------------
- **DOCUMENTATION_FOLDER_NAME**

---

<a href="../src/download.py#L39"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `recreate_docs`

```python
recreate_docs(clients: Clients, base: str) → bool
```

Recreate the docs folder and checks whether the docs folder is aligned with base branch/tag. 



**Args:**
 
 - <b>`clients`</b>:  Clients object containing Repository and Discourse API clients 
 - <b>`base`</b>:  tag to be compared to 



**Returns:**
 boolean representing whether any differences have occurred 


