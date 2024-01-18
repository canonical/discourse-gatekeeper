<!-- markdownlint-disable -->

<a href="../src/repository.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `repository.py`
Module for handling interactions with git repository. 

**Global Variables**
---------------
- **DOCUMENTATION_FOLDER_NAME**
- **GITHUB_HOSTNAME**
- **ORIGIN_NAME**
- **ACTIONS_USER_NAME**
- **ACTIONS_USER_EMAIL**
- **ACTIONS_PULL_REQUEST_TITLE**
- **ACTIONS_PULL_REQUEST_BODY**
- **PR_LINK_NO_CHANGE**
- **TAG_MESSAGE**
- **CONFIG_USER_SECTION_NAME**
- **CONFIG_USER_NAME**
- **CONFIG_USER_EMAIL**
- **BRANCH_PREFIX**
- **DEFAULT_BRANCH_NAME**
- **ACTIONS_COMMIT_MESSAGE**

---

<a href="../src/repository.py#L736"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `create_repository_client`

```python
create_repository_client(access_token: str | None, base_path: Path) → Client
```

Create a Github instance to handle communication with Github server. 



**Args:**
 
 - <b>`access_token`</b>:  Access token that has permissions to open a pull request. 
 - <b>`base_path`</b>:  Path where local .git resides in. 



**Raises:**
 
 - <b>`InputError`</b>:  if invalid access token or invalid git remote URL is provided. 



**Returns:**
 A Github repository instance. 


---

## <kbd>class</kbd> `Client`
Wrapper for git/git-server related functionalities. 

Attrs:  base_path: The root directory of the repository.  metadata: Metadata object of the charm  has_docs_directory: whether the repository has a docs directory  current_branch: current git branch used in the repository  current_commit: current commit checkout in the repository  branches: list of all branches 

<a href="../src/repository.py#L178"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(repository: Repo, github_repository: Repository) → None
```

Construct. 



**Args:**
 
 - <b>`repository`</b>:  Client for interacting with local git repository. 
 - <b>`github_repository`</b>:  Client for interacting with remote github repository. 


---

#### <kbd>property</kbd> branches

Return all local branches. 

---

#### <kbd>property</kbd> current_branch

Return the current branch. 

---

#### <kbd>property</kbd> current_commit

Return the current branch. 

---

#### <kbd>property</kbd> has_docs_directory

Return whether the repository has a docs directory. 

---

#### <kbd>property</kbd> metadata

Return the Metadata object of the charm. 



---

<a href="../src/repository.py#L372"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `create_branch`

```python
create_branch(branch_name: str, base: str | None = None) → Client
```

Create a new branch. 

Note that this will not switch branch. To create and switch branch, please pipe the two operations together: 

repository.create_branch(branch_name).switch(branch_name) 



**Args:**
 
 - <b>`branch_name`</b>:  name of the branch to be created 
 - <b>`base`</b>:  branch or tag to be branched from 



**Raises:**
 
 - <b>`RepositoryClientError`</b>:  if an error occur when creating a new branch 



**Returns:**
 Repository client object. 

---

<a href="../src/repository.py#L534"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `create_pull_request`

```python
create_pull_request(base: str) → PullRequest
```

Create pull request for changes in given repository path. 



**Args:**
 
 - <b>`base`</b>:  tag or branch against to which the PR is opened 



**Raises:**
 
 - <b>`InputError`</b>:  when the repository is not dirty, hence resulting on an empty pull-request 



**Returns:**
 Pull request object 

---

<a href="../src/repository.py#L630"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_file_content_from_tag`

```python
get_file_content_from_tag(path: str, tag_name: str) → str
```

Get the content of a file for a specific tag. 



**Args:**
 
 - <b>`path`</b>:  The path to the file. 
 - <b>`tag_name`</b>:  The name of the tag. 



**Returns:**
 The content of the file for the tag. 



**Raises:**
 
 - <b>`RepositoryTagNotFoundError`</b>:  if the tag could not be found in the repository. 
 - <b>`RepositoryFileNotFoundError`</b>:  if the file could not be retrieved from GitHub, more than  one file is returned or a non-file is returned 
 - <b>`RepositoryClientError`</b>:  if there is a problem with communicating with GitHub 

---

<a href="../src/repository.py#L508"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_pull_request`

```python
get_pull_request(branch_name: str) → PullRequest | None
```

Return open pull request matching the provided branch name. 



**Args:**
 
 - <b>`branch_name`</b>:  branch name to select open pull requests. 



**Raises:**
 
 - <b>`RepositoryClientError`</b>:  if more than one PR is open with the given branch name 



**Returns:**
 PullRequest object. If no PR is found, None is returned. 

---

<a href="../src/repository.py#L255"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_summary`

```python
get_summary(directory: str | None = 'docs') → DiffSummary
```

Return a summary of the differences against the most recent commit. 



**Args:**
 
 - <b>`directory`</b>:  constraint committed changes to a particular folder only. If None, all the  folders are committed. Default is the documentation folder. 



**Returns:**
 DiffSummary object representing the summary of the differences. 

---

<a href="../src/repository.py#L271"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `is_commit_in_branch`

```python
is_commit_in_branch(commit_sha: str, branch: str | None = None) → bool
```

Check if commit exists in a given branch. 



**Args:**
 
 - <b>`commit_sha`</b>:  SHA of the commit to be searched for 
 - <b>`branch`</b>:  name of the branch against which the check is done. When None, the current  branch is used. 



**Raises:**
 
 - <b>`RepositoryClientError`</b>:  when the commit is not found in the repository 



**Returns:**
  boolean representing whether the commit exists in the branch 

---

<a href="../src/repository.py#L576"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `is_dirty`

```python
is_dirty(branch_name: str | None = None) → bool
```

Check if repository path has any changes including new files. 



**Args:**
 
 - <b>`branch_name`</b>:  name of the branch to be checked against dirtiness 



**Returns:**
 True if any changes have occurred. 

---

<a href="../src/repository.py#L493"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `is_same_commit`

```python
is_same_commit(tag: str, commit: str) → bool
```

Return whether tag and commit coincides. 



**Args:**
 
 - <b>`tag`</b>:  name of the tag 
 - <b>`commit`</b>:  sha of the commit 



**Returns:**
 True if the two pointers coincides, False otherwise. 

---

<a href="../src/repository.py#L302"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `pull`

```python
pull(branch_name: str | None = None) → None
```

Pull content from remote for the provided branch. 



**Args:**
 
 - <b>`branch_name`</b>:  branch to be pulled from the remote 

---

<a href="../src/repository.py#L314"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `switch`

```python
switch(branch_name: str) → Client
```

Switch branch for the repository. 



**Args:**
 
 - <b>`branch_name`</b>:  name of the branch to switch to. 



**Returns:**
 Repository object with the branch switched. 

---

<a href="../src/repository.py#L606"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `tag_commit`

```python
tag_commit(tag_name: str, commit_sha: str) → None
```

Tag a commit, if the tag already exists, it is deleted first. 



**Args:**
 
 - <b>`tag_name`</b>:  The name of the tag. 
 - <b>`commit_sha`</b>:  The SHA of the commit to tag. 



**Raises:**
 
 - <b>`RepositoryClientError`</b>:  if there is a problem with communicating with GitHub 

---

<a href="../src/repository.py#L591"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `tag_exists`

```python
tag_exists(tag_name: str) → str | None
```

Check if a given tag exists. 



**Args:**
 
 - <b>`tag_name`</b>:  name of the tag to be checked for existence 



**Returns:**
 hash of the commit the tag refers to. 

---

<a href="../src/repository.py#L418"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `update_branch`

```python
update_branch(
    commit_msg: str,
    push: bool = True,
    force: bool = False,
    directory: str | None = 'docs'
) → Client
```

Update branch with a new commit. 



**Args:**
 
 - <b>`commit_msg`</b>:  commit message to be committed to the branch 
 - <b>`push`</b>:  push new changes to remote branches 
 - <b>`force`</b>:  when pushing to remove, use force flag 
 - <b>`directory`</b>:  constraint committed changes to a particular folder only. If None, all the  folders are committed. Default is the documentation folder. 



**Raises:**
 
 - <b>`RepositoryClientError`</b>:  if any error are encountered in the update process 



**Returns:**
 Repository client with the updated branch 

---

<a href="../src/repository.py#L562"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `update_pull_request`

```python
update_pull_request(branch: str) → None
```

Update and push changes to the given branch. 



**Args:**
 
 - <b>`branch`</b>:  name of the branch to be updated 

---

<a href="../repository/py/with_branch#L232"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `with_branch`

```python
with_branch(branch_name: str) → Iterator['Client']
```

Return a context for operating within the given branch. 

At the end of the 'with' block, the branch is switched back to what it was initially. 



**Args:**
 
 - <b>`branch_name`</b>:  name of the branch 



**Yields:**
 Context to operate on the provided branch 


---

## <kbd>class</kbd> `DiffSummary`
Class representing the summary of the dirty status of a repository. 

Attrs:  is_dirty: boolean indicated whether there is any delta  new: list of files added in the delta  removed: list of files removed in the delta  modified: list of files modified in the delta 




---

<a href="../src/repository.py#L78"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>classmethod</kbd> `from_raw_diff`

```python
from_raw_diff(diffs: Sequence[Diff]) → DiffSummary
```

Return a DiffSummary class from a sequence of git.Diff objects. 



**Args:**
 
 - <b>`diffs`</b>:  list of git.Diff objects representing the delta between two snapshots. 



**Returns:**
 DiffSummary class 


