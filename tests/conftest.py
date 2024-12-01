from pathlib import Path
from uuid import uuid4

from pytest import fixture

pytest_plugins = ["pytester"]


@fixture
def temp_perfetto_file_path(tmp_path: Path) -> Path:
    return tmp_path / f"{uuid4().hex}.json"
