<!-- markdownlint-disable -->

<a href="../src/commit.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `commit.py`
Module for handling interactions with git commit. 


---

<a href="../src/commit.py#L44"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `parse_git_show`

```python
parse_git_show(
    output: str,
    repository_path: Path
) → Iterator[FileAddedOrModified | FileDeleted]
```

Parse the output of a git show with --name-status into manageable data. 



**Args:**
 
 - <b>`output`</b>:  The output of the git show command. 
 - <b>`repository_path`</b>:  The path to the git repository. 



**Yields:**
 Information about each of the files that changed in the commit. 


---

## <kbd>class</kbd> `FileAddedOrModified`
File that was added, mofied or copied copied in a commit. 



**Attributes:**
 
 - <b>`path`</b>:  The location of the file on disk. 
 - <b>`content`</b>:  The content of the file. 





---

## <kbd>class</kbd> `FileDeleted`
File that was deleted in a commit. 



**Attributes:**
 
 - <b>`path`</b>:  The location of the file on disk. 





