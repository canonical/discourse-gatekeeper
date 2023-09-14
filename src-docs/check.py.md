<!-- markdownlint-disable -->

<a href="../src/check.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `check.py`
Module for running checks. 

**Global Variables**
---------------
- **DOCUMENTATION_TAG**

---

<a href="../src/check.py#L52"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_path_with_diffs`

```python
get_path_with_diffs(
    actions: Iterable[UpdatePageAction | UpdateGroupAction | UpdateExternalRefAction]
) → PathsWithDiff
```

Generate the paths that have either local or server content changes. 



**Args:**
 
 - <b>`actions`</b>:  The update actions to track diffs for. 



**Returns:**
 The paths that have differences. 


---

<a href="../src/check.py#L158"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `conflicts`

```python
conflicts(
    actions: Iterable[CreatePageAction | CreateGroupAction | CreateExternalRefAction | NoopPageAction | NoopGroupAction | NoopExternalRefAction | UpdatePageAction | UpdateGroupAction | UpdateExternalRefAction | DeletePageAction | DeleteGroupAction | DeleteExternalRefAction],
    repository: Client,
    user_inputs: UserInputs
) → Iterator[Problem]
```

Check whether actions have any content conflicts. 

There are two types of conflicts. The first is where the local content is different to what is on the server and both the local content and the server content is different from the base. This means that there were edits on the server which have not been merged into git and the PR is making changes to the same page. 

The second type of conflict is a logical conflict which arises out of that there are at least some changes on the server that have not been merged into git yet and the branch is proposing to make changes to the documentation as well. This means that there could be changes made on the server which logically conflict with proposed changes in the PR. These conflicts can be supppressed using the discourse-ahead-ok tag on the commit that the action is running on. 



**Args:**
 
 - <b>`actions`</b>:  The actions to check. 
 - <b>`repository`</b>:  Client for repository interactions. 
 - <b>`user_inputs`</b>:  Configuration from the user. 



**Yields:**
 A problem for each action with a conflict 


---

## <kbd>class</kbd> `PathsWithDiff`
Keeps track of paths that have any differences. 

Attrs:  base_local_diffs: The paths that have a difference between the base and local content.  base_server_diffs: The paths that have a difference between the local and server content. 





---

## <kbd>class</kbd> `Problem`
Details about a failed check. 

Attrs:  path: Unique identifier for the file and discourse topic with the problem  description: A summary of what the problem is and how to resolve it. 





