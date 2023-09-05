# Upload Charm Documentation

*This action is still in alpha, breaking changes could occur.*

This action automates uploading documentation from the `docs` folder in a
repository to discourse which is how the charm documentation is published to
charmhub.

## Getting Started

### Sync docs

1. Create the `docs` folder in the repository.
2. Optionally, create a file `docs/index.md` for any content you would like to
    display above the navigation table on discourse. This content does not get
    published to charmhub and is only visible on discourse.
3. Within the `docs` folder, create directories for page groups (e.g., for all
    tutorials) and markdown files (`*.md`) for individual pages. On charmhub,
    the groupings on the navigation panel will be named based on the name of
    the directory after replacing `_` and `-` with spaces and appliying the
    [`str.title`](https://docs.python.org/3/library/stdtypes.html#str.title)
    function to it. The name of pages is based on whatever of the following is
    available, in order: (1) the first level 1 heading (e.g., `# <heading>`) in
    the file, the first line in the file or the name of the file treated in the
    same way as the name of groupings.

    If you have existing documentation on discourse, you can retrieve the
    markdown version by changing the link to the topic in your browser from
    `https://discourse.charmhub.io/t/<slug>/<topic id>` to
    `https://discourse.charmhub.io/raw/<topic id>`. *Future plans for this
    action include automating this migration by pulling the content down and
    creating a PR for you to review in the repository.*

    Note that the action may change the order of how groups and pages are
    displayed in the navigation pane. The action will sort them alphabetically.
4. Optionally, remove the current `docs` key from `metadata.yaml` if you would
    like the action to create its own topics on discourse rather than re-use
    any existing topics. This means that if, for some reason, you don't like
    what the action does, you can easily revert back to the previous
    documentation. Be sure to file an issue with the reason if the action does
    something unexpected or you would prefer it to do something different.
5. Add this action to your desired workflow. For example:

    ```yaml
    jobs:
      publish-docs:
        name: Publish docs
        runs-on: ubuntu-22.04
        steps:
          - uses: actions/checkout@v3
          - name: Publish documentation
            uses: canonical/upload-charm-docs@stable
            id: publishDocumentation
            with:
              discourse_host: discourse.charmhub.io
              discourse_api_username: ${{ secrets.DISCOURSE_API_USERNAME }}
              discourse_api_key: ${{ secrets.DISCOURSE_API_KEY }}
              github_token: ${{ secrets.GITHUB_TOKEN }}
          - name: Show index page
            run: echo '${{ steps.publishDocumentation.outputs.index_url }}'
    ```

    This action requires an API username and key to discourse. For Canonical
    staff, please file a ticket with IS to request one. Note that there is a
    rate limit on the number of topics that can be created by a user per day on
    discourse. If you encounter this issue, the action will fail and report
    that as the reason. It may help to space out adopting this action if you
    are planning to use it for multiple charms or to use different users for
    each charm. Note that other rate limits also apply which is why execution
    might look like it is stalled for a short period and then resume. The
    action will gracefully wait in case of throttling up to a maximum of 10
    minutes.

    There is a nice parameter, `dry_run`, which will do everything except
    make changes on discourse and log what would have happened. This will help
    you see what the action would have done.
6. Check the logs for the URL to the index topic that the action created. This
    is also available under the `index_url` output of the action. This needs to
    be added to the `metadata.yaml` under the `docs` key.

### Migrate docs

1. Create a `docs` key in `metadata.yaml` with the link to the documentation on
    charmhub.
2. Add the action to your desired workflow as mentioned in step 5 of
    [Sync docs section](#sync-docs) with github_token. For example:

    ```yaml
    jobs:
      publish-docs:
        name: Publish docs
        runs-on: ubuntu-22.04
        steps:
          - uses: actions/checkout@v3
          - name: Publish documentation
            uses: canonical/upload-charm-docs@stable
            id: publishDocumentation
            with:
              discourse_host: discourse.charmhub.io
              discourse_api_username: ${{ secrets.DISCOURSE_API_USERNAME }}
              discourse_api_key: ${{ secrets.DISCOURSE_API_KEY }}
              github_token: ${{ secrets.GITHUB_TOKEN }}
    ```

    a branch name with `upload-charm-docs/migrate` will be created and a pull
    request named `[upload-charm-docs] Migrate charm docs` will be created
    targeting the default branch of the repository. In order to ensure that the
    branches can be created successfully, please make sure that there are no
    existing branches clashing with the name above. Please note that the
    `dry_run` input has no effect on migrate mode.

The action will now compare the discourse topics with the files and directories
under the `docs` directory and make any changes based on differences.
Additional recommended steps:

* Add the action in dry run mode to run on every PR. This will mean that you
  will see all the changes that would be made by the PR once you are ready to
  publish a new version of the charm and documentation.
* Add the action in dry run mode on publishes to `edge` to see what changes to
  the documentation will be made once you publish to `stable`.

## Discourse Documentation Edits

To ensure that contributions to the documentation on discourse are not
overridden, the action compares the content that was last pushed to discourse
with the current documentation on discourse and any proposed changes. If there
are changes both on discourse and in the repository, the action will prompt you
to resolve those conflicts by editing the documentation on discourse and on the
repository. Be sure to explain the reasoning for any changes on discourse.

The content that was last pushed to discourse is determined by getting the
content from a given file from a commit with the
`upload-charm-docs/base-content` tag. If the tag does not exist, the action will
fail and request for the tag to be created.

In addition to page-by-page conflict detection, the action will check whether
there are both (1) unmerged community contributions and (2) proposed
documentation changes in a given PR. If both are true even if there are no
page-by-page conflicts, the action will ask that the community contributions are
merged first and any logical conflicts are resolved between the proposed new
documentation and the changes on discourse.

For example, if there are community contributions on `docs/getting-started.md`
that have not been merged into `main` and a PR proposes changes to
`docs/architecture.md`, this will be considered a conflict as the change to
`docs/architecture.md` could make changes to the documentation that mean that
the changes to `docs/getting-started.md` are no longer accurate.

If, after checking the community contributions on discourse, you determine that
there are no logical conflicts, the `upload-charm-docs/discourse-ahead-ok` tag
can be applied to the latest commit in the PR which will allow the action to
proceed assuming there are no page-by-page conflicts.

## Contents Index

The `docs/index.md` file may contain a `# contents` section which is used to
customize the generation of the navigation table on discourse. Everything from
this section up to the next header (identified by a line starting with `#`) or
the end of the file will be removed from the index page and be replaced with the
navigation table on discourse. For example the following section in
`docs/index.md`:

```markdown
# Contents

1. [Reference](reference)
  1. [Integrations](reference/integrations.md)
```

Would result in the following navigation table on discourse:

```markdown
# Navigation

| level | path | navlink |
| --- | --- | --- |
| 1 | reference | [Reference]() |
| 2 | reference-integrations | [Integrations](/t/nginx-ingress-integrator-docs-reference-integrations/7756) |
```

The following are example valid permutations of the contents section in
`index.md`:

```markdown
# Contents

1. [Reference](reference)
  a. [Integrations](reference/integrations.md)

# Contents

* [Reference](reference)
  * [Integrations](reference/integrations.md)

# Contents

- [Reference](reference)
  - [Integrations](reference/integrations.md)

# Contents

- [Reference](reference)
  1. [Integrations](reference/integrations.md)
```

The links can be one of the following:

* A local link to a directory (e.g., [Tutorials](tutorials) which links to the
  `tutorials` directory)
* A local link to a file (e.g., [Getting Started](tutorials/getting-started.md)
  which links to the `tutorials/getting-started.md` file)

`*.md` files and directories in `docs` not listed in the contents index will be
added in alphabetical order after any items that are listed. This is to ensure
backwards compatibility. References are checked for validity. A link to a file
or directory that does not exist will result in an error.

### Hidden Items

Items on the contents index can be commented out which will mean the item on the
navigation table won't have a level. This will mean that the item is not shown
on the navigation but can still be used in links.

### Discourse Translation

* The list hierarchy indicates the level on the navigation table, this is
  checked against the file structure and results in an error/ warning to the
  user if it is not a match
* Files and directories don’t have to be listed, if they are not listed they are
  injected in the appropriate location after any listed items (for backwards
  compatibility and ease of use) in alphabetical order

## Developers

### Risk-based branching

This action uses the notion of risks, similarly to what used in SNAP (see 
[here](https://snapcraft.io/docs/channels) for a description and explanation of these concepts). 
We currently only provide support on one single track (say latest), with the following 
branching naming convention:

* [main](https://github.com/canonical/upload-charm-docs/tree/main) corresponds to the edge risk
* [stable](https://github.com/canonical/upload-charm-docs/tree/stable) corresponds to the stable version of the action

We therefore generally advise you to pick the risk channel that best fits to your need. 

### End-to-End Integration Tests

When merging a PR, we make sure the code follows all code conventions (linting), unit-tests and 
integration tests. **Edge version are however NOT checked against full end-to-end integration tests**. 

<!-- LINK BELOW TO BE CHANGED -->
End-to-End tests are implemented in a separated [test repository](https://github.com/deusebio/repo-test), 
and run as scheduled workflows against the edge branch. When working on large and impactful feature, 
we generally suggest to test your branch PR against End-to-End tests even before merging. To do so, 
follow these steps:

1. Fork the [test repository](https://github.com/deusebio/repo-test)
2. Amend the E2E workflows to point to your PR branch, i.e. 
```yaml
      name: Publish documentation
      uses: canonical/upload-charm-docs@your-pr-branch # CHANGE HERE
```
3. Raise a PR against the test-repository. This PR will not be merged but it will allow you to tests
    your changes

Periodically, we review the latest changes on edge branches and we rebase lower risks branches (
e.g. stable) onto higher risk branches (e.g. edge). 