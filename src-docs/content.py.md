<!-- markdownlint-disable -->

<a href="../src/content.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `content.py`
Module for checking conflicts using 3-way merge and create content based on a 3 way merge. 


---

<a href="../src/content.py#L20"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `conflicts`

```python
conflicts(base: str, theirs: str, ours: str) → str | None
```

Check for merge conflicts based on the git merge algorithm. 



**Args:**
 
 - <b>`base`</b>:  The starting point for both changes. 
 - <b>`theirs`</b>:  The other change. 
 - <b>`ours`</b>:  The local change. 



**Returns:**
 The description of the merge conflicts or None if there are no conflicts. 


---

<a href="../src/content.py#L38"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `merge`

```python
merge(base: str, theirs: str, ours: str) → str
```

Create the merged content based on the git merge algorithm. 



**Args:**
 
 - <b>`base`</b>:  The starting point for both changes. 
 - <b>`theirs`</b>:  The other change. 
 - <b>`ours`</b>:  The local change. 



**Returns:**
 The merged content. 



**Raises:**
 
 - <b>`ContentError`</b>:  if there are merge conflicts. 


---

<a href="../src/content.py#L100"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `diff`

```python
diff(first: str, second: str) → str
```

Show the difference between two strings. 



**Args:**
 
 - <b>`first`</b>:  One of the strings to compare. 
 - <b>`second`</b>:  One of the strings to compare. 



**Returns:**
 The diff between the two strings. 


