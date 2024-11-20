# What is a pytest plugin?

Pytest's extensibility comes from its *plugin* system. Pytest loads custom, pip installable plugins
by looking for an entrypoint called "pytest-11" in a python project's distribution. Plugins loaded
through said entrypoint may define custom hooks, 
[similar to what the xdist package does package](https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/newhooks.py).

A plugin extends pytest by implementing specific functions well-known to pytest, these functions are
called *'hooks'*. The hooks in the plugin themselves do nothing on their own, and rely on pytest to
call these methods, similar to the [observer
pattern](https://en.wikipedia.org/wiki/Observer_pattern).

# Hooks
Pytest offers six types of hooks, which are: (1) Bootstrapping hooks, (2) Initialization Hooks, (3)
Collection Hooks, (4) Test Running hooks, (5) Reporting hooks, and (6) Debugging/Interaction hooks.

## Bootrapping hooks
Bootstrapping hooks are called for plugins registered early enough. Only internal and setuptools
plugins (find out more about setuptools plugins) are able to make use of bootstrapping plugins,
making them relatively useless for plugins that do not fit this criteria.

## Initialization hooks
Initialization hooks offer plugins the opportunity to initialize themselves, and to customize
pytest's API. At this stage, a plugin may: 
* Register custom CLI arguments to pytest
  ([`pytest_addoption`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_addoption))
  which may be used to configure the plugin itself;
* Register pytest hooks in order to further extend pytest's plugin system, allowing other plugins to 
  extend the plugin ([`pytest_addhooks`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_addhooks));
* Perform initial configuration ([`pytest_configure`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_configure));

During the initialization phase, the plugin is notified of when the pytest session starts
([`pytest_sessionstart`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_configure)),
and finishes ([`pytest_sessionfinish`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_sessionfinish)).

## Collection hooks
In the test collection phase, pytest scours the project's test and source code directory, finding
all existing tests and [doctests](https://docs.pytest.org/en/stable/how-to/doctest.html). As a
project grows, and the number of tests accumulate, the runtime of the collection phase also tends to
grow. In a project with thousands of unit tests, one may expect pytest to spend several seconds in
the collection phase. Although this may seem miniscule for a CI/CD pipeline, time spent in the
collection phase becomes apparent very quickly, as one cannot run a test without first going through
the collection phase.

Collection hooks allow a plugin to control and observe pytest's collection phase, giving a plugin
the power to:
* Ignore certain paths from being visited during collection ([`pytest_ignore_collect`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_ignore_collect));
* Perform some action before collection ([`pytest_collection`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_collection));
* Generate parameterized tests ([`pytest_generate_tests`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_generate_tests));
* Filter, and re-order the collected tests after collection has completed ([`pytest_collection_modifyitems`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_collection_modifyitems));
* Know when collection has finished, including any further alterations from `pytest_collection_modifyitems` ([`pytest_collection_finish`](https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_collection_finish));






