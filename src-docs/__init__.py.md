<!-- markdownlint-disable -->

<a href="../src/__init__.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `__init__.py`
Library for uploading docs to charmhub. 

**Global Variables**
---------------
- **DRY_RUN_NAVLINK_LINK**
- **FAIL_NAVLINK_LINK**
- **DOCUMENTATION_FOLDER_NAME**
- **DOCUMENTATION_TAG**
- **DEFAULT_BRANCH_NAME**
- **GETTING_STARTED**

---

<a href="../src/__init__.py#L75"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `run_reconcile`

```python
run_reconcile(
    clients: Clients,
    user_inputs: UserInputs
) → ReconcileOutputs | None
```

Upload the documentation to charmhub. 



**Args:**
 
 - <b>`clients`</b>:  The clients to interact with things like discourse and the repository. 
 - <b>`user_inputs`</b>:  Configurable inputs for running discourse-gatekeeper. 



**Returns:**
 ReconcileOutputs object with the result of the action. None, if there is no reconcile. 



**Raises:**
 
 - <b>`InputError`</b>:  if there are any problems with the contents index or executing any of the  actions. 
 - <b>`TaggingNotAllowedError`</b>:  if the reconcile tries to tag a branch which is not the main base  branch 


---

<a href="../src/__init__.py#L191"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `run_migrate`

```python
run_migrate(clients: Clients, user_inputs: UserInputs) → MigrateOutputs | None
```

Migrate existing docs from charmhub to local repository. 



**Args:**
 
 - <b>`clients`</b>:  The clients to interact with things like discourse and the repository. 
 - <b>`user_inputs`</b>:  Configurable inputs for running discourse-gatekeeper. 



**Returns:**
 MigrateOutputs providing details on the action performed and a link to the Pull Request containing migrated documentation. None if there is no migration. 


---

<a href="../src/__init__.py#L255"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `pre_flight_checks`

```python
pre_flight_checks(clients: Clients, user_inputs: UserInputs) → bool
```

Perform checks to make sure the repository is in a consistent state. 



**Args:**
 
 - <b>`clients`</b>:  The clients to interact with things like discourse and the repository. 
 - <b>`user_inputs`</b>:  Configurable inputs for running discourse-gatekeeper. 



**Returns:**
 Boolean representing whether the checks have all been passed. 


