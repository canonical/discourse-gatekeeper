<!-- markdownlint-disable -->

<a href="../src/discourse.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `discourse.py`
Interface for Discourse interactions. 


---

<a href="../src/discourse.py#L498"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `create_discourse`

```python
create_discourse(
    hostname: str,
    category_id: str,
    api_username: str,
    api_key: str
) → Discourse
```

Create discourse client. 



**Args:**
 
 - <b>`hostname`</b>:  The Discourse server hostname. 
 - <b>`category_id`</b>:  The category to use for topics. 
 - <b>`api_username`</b>:  The discourse API username to use for interactions with the server. 
 - <b>`api_key`</b>:  The discourse API key to use for interactions with the server. 



**Returns:**
 A discourse client that is connected to the server. 



**Raises:**
 InputError: if the api_username and api_key arguments are not strings or empty, if the protocol has been included in the hostname, the hostname is not a string or the category_id is not an integer or a string that can be converted to an integer. 


---

## <kbd>class</kbd> `Discourse`
Interact with a discourse server. 

Attrs:  host: The host of the discourse server. 

<a href="../src/discourse.py#L77"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(host: str, api_username: str, api_key: str, category_id: int) → None
```

Construct. 



**Args:**
 
 - <b>`host`</b>:  The HTTP protocol and hostname for discourse (e.g., https://discourse). 
 - <b>`api_username`</b>:  The username to use for API requests. 
 - <b>`api_key`</b>:  The API key for requests. 
 - <b>`category_id`</b>:  The category identifier to put the topics into. 


---

#### <kbd>property</kbd> host

The HTTP protocol and hostname for discourse (e.g., https://discourse). 



---

<a href="../src/discourse.py#L290"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `absolute_url`

```python
absolute_url(url: str) → str
```

Get the URL including base path for a topic. 



**Args:**
 
 - <b>`url`</b>:  The relative or absolute URL. 



**Returns:**
 The url with the base path. 

---

<a href="../src/discourse.py#L316"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `check_topic_read_permission`

```python
check_topic_read_permission(url: str) → bool
```

Check whether the credentials have read permission on a topic. 

Uses whether retrieve topic succeeds as indication whether the read permission is available. 



**Args:**
 
 - <b>`url`</b>:  The URL to the topic. Assume it includes the slug and id of the topic as the last  2 elements of the url. 



**Returns:**
 Whether the credentials have read permissions to the topic. 

---

<a href="../src/discourse.py#L302"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `check_topic_write_permission`

```python
check_topic_write_permission(url: str) → bool
```

Check whether the credentials have write permission on a topic. 



**Args:**
 
 - <b>`url`</b>:  The URL to the topic. Assume it includes the slug and id of the topic as the last  2 elements of the url. 



**Returns:**
 Whether the credentials have write permissions to the topic. 

---

<a href="../src/discourse.py#L409"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `create_topic`

```python
create_topic(title: str, content: str) → str
```

Create a new topic. 



**Args:**
 
 - <b>`title`</b>:  The title of the topic. 
 - <b>`content`</b>:  The content for the first post in the topic. 



**Returns:**
 The URL to the topic. 



**Raises:**
 
 - <b>`DiscourseError`</b>:  if anything goes wrong during topic creation. 

---

<a href="../src/discourse.py#L439"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `delete_topic`

```python
delete_topic(url: str) → str
```

Delete a topic. 



**Args:**
 
 - <b>`url`</b>:  The URL to the topic. 



**Returns:**
 The link to the deleted topic. 



**Raises:**
 
 - <b>`DiscourseError`</b>:  if authentication fails if the server refuses to delete the topic, if  the topic is not found or if anything else has gone wrong. 

---

<a href="../src/discourse.py#L372"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `retrieve_topic`

```python
retrieve_topic(url: str) → str
```

Retrieve the topic content. 



**Args:**
 
 - <b>`url`</b>:  The URL to the topic. Assume it includes the slug and id of the topic as the last  2 elements of the url. 



**Returns:**
 The content of the first post in the topic. 



**Raises:**
 
 - <b>`DiscourseError`</b>:  if authentication fails, if the server refuses to return the requested  topic or if the topic is not found. 

---

<a href="../src/discourse.py#L133"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `topic_url_valid`

```python
topic_url_valid(url: str) → _ValidationResultValid | _ValidationResultInvalid
```

Check whether a url to a topic is valid. Assume the url is well formatted. 

Validations:  1. The URL must start with the base path configured during construction.  2. The URL must resolve on a discourse HEAD request.  3. The URL must have 3 components in its path.  4. The first component in the path must be the literal 't'.  5. The second component in the path must be the slug to the topic which must have at  least 1 character.  6. The third component must the the topic id as an integer. 



**Args:**
 
 - <b>`url`</b>:  The URL to check. 



**Returns:**
 Whether the URL is a valid topic URL. 

---

<a href="../src/discourse.py#L462"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `update_topic`

```python
update_topic(
    url: str,
    content: str,
    edit_reason: str = 'Charm documentation updated'
) → str
```

Update the first post of a topic. 



**Args:**
 
 - <b>`url`</b>:  The URL to the topic. 
 - <b>`content`</b>:  The content for the first post in the topic. 
 - <b>`edit_reason`</b>:  The reason the edit was made. 



**Returns:**
 The link to the updated topic. 



**Raises:**
 
 - <b>`DiscourseError`</b>:  if authentication fails, if the server refuses to update the first post  in the topic or if the topic is not found. 


