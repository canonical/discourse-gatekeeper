<!-- markdownlint-disable -->

<a href="../src/gatekeeper/types_.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `types_.py`
Types for uploading docs to charmhub. 



---

## <kbd>class</kbd> `ActionReport`
Post execution report for an action. 

Attrs:  table_row: The navigation table entry, None for delete or index actions.  location: The URL that the action operated on, None for groups or if a create action was  skipped, if running in reconcile mode.  Path to migrated file, if running in migration mode. None on action failure.  result: The action execution result.  reason: The reason, None for success reports. 





---

## <kbd>class</kbd> `ActionResult`
Result of taking an action. 

Attrs:  SUCCESS: The action succeeded.  SKIP: The action was skipped.  FAIL: The action failed. 





---

## <kbd>class</kbd> `ContentChange`
Represents a change to the content. 

Attrs:  base: The content which is the base for comparison.  server: The content on the server.  local: The content on the local disk. 





---

## <kbd>class</kbd> `CreateExternalRefAction`
Represents a external reference to be created. 

Attrs:  navlink_value: The external reference. 





---

## <kbd>class</kbd> `CreateGroupAction`
Represents a group to be created. 





---

## <kbd>class</kbd> `CreateIndexAction`
Represents an index page to be created. 

Attrs:  title: The title of the index page.  content: The content including the navigation table. 





---

## <kbd>class</kbd> `CreatePageAction`
Represents a page to be created. 

Attrs:  content: The documentation content. 





---

## <kbd>class</kbd> `DeleteExternalRefAction`
Represents an external reference to be deleted. 





---

## <kbd>class</kbd> `DeleteGroupAction`
Represents a group to be deleted. 





---

## <kbd>class</kbd> `DeletePageAction`
Represents a page to be deleted. 

Attrs:  content: The documentation content. 





---

## <kbd>class</kbd> `DocumentMeta`
Represents a document to be migrated from the index table. 

Attrs:  link: Link to content to read from.  table_row: Document row that is the source of document file. 





---

## <kbd>class</kbd> `GitkeepMeta`
Represents an empty directory from the index table. 

Attrs:  table_row: Empty group row that is the source of .gitkeep file. 





---

## <kbd>class</kbd> `Index`
Information about the local and server index page. 

Attrs:  server: The index page on the server.  local: The local index file contents.  name: The name of the charm. 





---

## <kbd>class</kbd> `IndexContentChange`
Represents a change to the content of the index. 

Attrs:  old: The previous content.  new: The new content. 





---

## <kbd>class</kbd> `IndexContentsListItem`
Represents an item in the contents table. 

Attrs:  hierarchy: The number of parent items to the root of the list  reference_title: The name of the reference  reference_value: The link to the referenced item  rank: The number of preceding elements in the list at any hierarchy  hidden: Whether the item should be displayed on the navigation table  table_path: The path for the item on the table.  is_external: Whether the item is an external reference. 


---

#### <kbd>property</kbd> is_external

Whether the row is an external reference. 



**Returns:**
  Whether the item in the table is an external item. 

---

#### <kbd>property</kbd> table_path

The table path for the item. 

In the case of a HTTP reference, changes http://canonical.com/1 to http,canonical,com,1 removing the HTTP protocol characters so that the path conforms to the path in the non-HTTP case. Any remaining characters not allowed in the path are also removed. For a non-HTTP case, removes the file suffix and splits on / to built the path. 



**Returns:**
  The table path for the item. 




---

## <kbd>class</kbd> `IndexDocumentMeta`
Represents an index file document. 

Attrs:  content: Contents to write to index file. 





---

## <kbd>class</kbd> `IndexFile`
Information about a documentation page. 

Attrs:  title: The title for the index.  content: The local content of the index. 





---

## <kbd>class</kbd> `Metadata`
Information within metadata file. Refer to: https://juju.is/docs/sdk/metadata-yaml. 

Only name and docs are the fields of interest for the scope of this module. 

Attrs:  name: Name of the charm.  docs: A link to a documentation cover page on Discourse. 





---

## <kbd>class</kbd> `MigrateOutputs`
Output provided by the reconcile workflow. 

Attrs:  action: Action taken on the PR  pull_request_url: url of the pull-request when relevant 





---

## <kbd>class</kbd> `MigrationFileMeta`
Metadata about a document to be migrated. 

Attrs:  path: The full document path to be written to. 





---

## <kbd>class</kbd> `Navlink`
Represents navlink of a table row of the navigation table. 

Attrs:  title: The title of the documentation page.  link: The relative URL to the documentation page or None if there is no link.  hidden: Whether the item should be displayed on the navigation table. 





---

## <kbd>class</kbd> `NavlinkChange`
Represents a change to the navlink. 

Attrs:  old: The previous navlink.  new: The new navlink. 





---

## <kbd>class</kbd> `NoopExternalRefAction`
Represents an external reference with no required changes. 





---

## <kbd>class</kbd> `NoopGroupAction`
Represents a group with no required changes. 





---

## <kbd>class</kbd> `NoopIndexAction`
Represents an index page with no required changes. 

Attrs:  content: The content including the navigation table.  url: The URL to the index page. 





---

## <kbd>class</kbd> `NoopPageAction`
Represents a page with no required changes. 

Attrs:  content: The documentation content of the page. 





---

## <kbd>class</kbd> `Page`
Information about a documentation page. 

Attrs:  url: The link to the page.  content: The documentation text of the page. 





---

## <kbd>class</kbd> `PathInfo`
Represents a file or directory in the docs directory. 

Attrs:  local_path: The path to the file on the local disk.  level: The number of parent directories to the docs folder including the docs folder.  table_path: The computed table path based on the disk path relative to the docs folder.  navlink_title: The title of the navlink.  alphabetical_rank: The rank of the path info based on alphabetically sorting all relevant  path infos.  navlink_hidden: Whether the item should be displayed on the navigation table 





---

## <kbd>class</kbd> `PullRequestAction`
Result of taking an action. 

Attrs:  OPENED: A new PR has been opened.  CLOSED: An existing PR has been closed.  UPDATED: An existing PR has been updated. 





---

## <kbd>class</kbd> `ReconcileOutputs`
Output provided by the reconcile workflow. 

Attrs:  index_url: url with the root documentation topic on Discourse  topics: List of urls with actions  documentation_tag: commit sha to which the tag was created 





---

## <kbd>class</kbd> `TableRow`
Represents one parsed row of the navigation table. 

Attrs:  level: The number of parents, is 1 if there is no parent.  path: The a unique string identifying the row.  navlink: The title and relative URL to the documentation page.  is_group: Whether the row is the parent of zero or more other rows. 


---

#### <kbd>property</kbd> is_group

Whether the row is a group of pages. 



---

<a href="../src/gatekeeper/types_.py#L174"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `is_external`

```python
is_external(server_hostname: str) → bool
```

Whether the row is an external reference. 



**Args:**
 
 - <b>`server_hostname`</b>:  The hostname of the discourse server. 



**Returns:**
 Whether the item in the table is an external item. 

---

<a href="../src/gatekeeper/types_.py#L190"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `to_markdown`

```python
to_markdown(server_hostname: str) → str
```

Convert to a line in the navigation table. 



**Args:**
 
 - <b>`server_hostname`</b>:  The hostname of the discourse server. 



**Returns:**
 The line in the navigation table. 


---

## <kbd>class</kbd> `UpdateExternalRefAction`
Represents an external reference to be updated. 





---

## <kbd>class</kbd> `UpdateGroupAction`
Represents a group to be updated. 





---

## <kbd>class</kbd> `UpdateIndexAction`
Represents an index page to be updated. 

Attrs:  content_change: The change to the content including the navigation table.  url: The URL to the index page. 





---

## <kbd>class</kbd> `UpdatePageAction`
Represents a page to be updated. 

Attrs:  content_change: The change to the documentation content. 





---

## <kbd>class</kbd> `UserInputs`
Configurable user input values used to run discourse-gatekeeper. 

Attrs:  discourse: The configuration for interacting with discourse.  dry_run: If enabled, only log the action that would be taken. Has no effect in migration  mode.  delete_pages: Whether to delete pages that are no longer needed. Has no effect in  migration mode.  github_access_token: A Personal Access Token(PAT) or access token with repository access.  Required in migration mode.  commit_sha: The SHA of the commit the action is running on.  base_branch: The main branch against which the syncs act on.  charm_dir: Directory the charm is located in. 





---

## <kbd>class</kbd> `UserInputsDiscourse`
Configurable user input values used to run discourse-gatekeeper. 

Attrs:  hostname: The base path to the discourse server.  category_id: The category identifier to use on discourse for all topics.  api_username: The discourse API username to use for interactions with the server.  api_key: The discourse API key to use for interactions with the server. 





