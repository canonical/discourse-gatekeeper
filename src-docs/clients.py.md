<!-- markdownlint-disable -->

<a href="../src/gatekeeper/clients.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `clients.py`
Module for Client class. 


---

<a href="../src/gatekeeper/clients.py#L27"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_clients`

```python
get_clients(user_inputs: UserInputs, base_path: Path) → Clients
```

Return Clients object. 



**Args:**
 
 - <b>`user_inputs`</b>:  inputs provided via environment 
 - <b>`base_path`</b>:  path where the git repository is stored 



**Returns:**
 Clients object embedding both Discourse API and Repository clients 


---

## <kbd>class</kbd> `Clients`
Collection of clients needed during execution. 

Attrs:  discourse: Discourse client.  repository: Client for the repository. 





