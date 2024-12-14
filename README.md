# ☠️ Perfsephone, the pytest embedded profiler.
Perfsephone is a pytest plugin that profiles tests running under pytest, whose results can be
visualized using the [perfetto UI](https://perfetto.dev/), or chrome's builtin trace visualizer
[about:tracing](about:tracing).

![A perfsephone generated trace file of FastAPI's test suite, visualized using ui.perfetto.dev](images/image.png)
*A perfsephone generated trace file of FastAPI's test suite, visualized using ui.perfetto.dev*

# Getting started
## Installation
### pip
```bash
pip install git+https://github.com/lucamuscat/perfsephone.git
```

## Generating a trace
In order to generate a trace using perfsephone, add the `--perfetto=<FILE PATH>` flag to your pytest
invocation:

`pytest --perfetto=./trace.json`

