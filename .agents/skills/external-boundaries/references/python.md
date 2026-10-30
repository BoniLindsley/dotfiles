# Python and pytest

Mechanics for the external-boundaries skill in pytest.
Read `../SKILL.md` first.

- Mark tests that need the external thing `integration`,
  and end-to-end tests also `e2e`.
  Register both in the pytest configuration with a description.
  Unit tests have no mark.
- `-m "not integration"` runs the unit tests only,
  and must still reach the coverage target.
  `-m e2e` confirms the hard-coded cases.
- Skip in a fixture when the external thing is missing,
  with the reason, so that every test needing it skips the same way.
- Store cases as data files next to the tests,
  one file per case, parametrized by file name.
  Find large data through an option or an environment variable,
  and skip when it is not given.
- Add a `--record` option that rewrites the recorded outputs
  from the external thing instead of comparing them.
- To run a unit test on real output,
  give its output fixture a second parameter,
  marked `integration` and skipped unless an option asks for it.

Example, with an adapter `run_tool` and a consumer `summarise`:

```toml
[tool.pytest.ini_options]
markers = [
  "integration: tests that need an external program, service or its output",
  "e2e: end-to-end tests of hard-coded cases through the external program",
]
```

```python
# conftest.py

# Standard libraries.
import json
import pathlib
import shutil

from typing import Any, Dict

# External dependencies.
import pytest

CASES = sorted((pathlib.Path(__file__).parent / "cases").glob("*.json"))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--record",
        action="store_true",
        help="Rewrite recorded outputs in case files from the real tool.",
    )
    parser.addoption(
        "--real-output",
        action="store_true",
        help="Also run unit tests on output from the real tool.",
    )


@pytest.fixture(name="tool")
def fixture_tool() -> str:
    path = shutil.which("tool")
    if path is None:
        pytest.skip("tool not found")
    return path


@pytest.fixture(name="case", params=CASES, ids=lambda path: path.stem)
def fixture_case(request: pytest.FixtureRequest) -> Dict[str, Any]:
    case = json.loads(request.param.read_text(encoding="utf-8"))
    case["path"] = request.param
    return case
```

```python
# test_tool.py

# Standard libraries.
import json

from typing import Any, Dict

# External dependencies.
import pytest

# Internal modules.
from package.tool import run_tool, summarise


@pytest.fixture(
    name="output",
    params=["recorded", pytest.param("real", marks=pytest.mark.integration)],
)
def fixture_output(
    request: pytest.FixtureRequest, case: Dict[str, Any]
) -> Any:
    if request.param == "recorded":
        if "output" not in case:
            pytest.skip("no recorded output; run with --record")
        return case["output"]
    if not request.config.getoption("--real-output"):
        pytest.skip("real output not requested; use --real-output")
    tool = request.getfixturevalue("tool")
    return run_tool(tool, **case["input"])


class TestSummarise:
    def test_case(self, case: Dict[str, Any], output: Any) -> None:
        assert summarise(output) == case["expected"]


@pytest.mark.integration
class TestRunTool:
    def test_case(
        self,
        case: Dict[str, Any],
        tool: str,
        request: pytest.FixtureRequest,
    ) -> None:
        output = run_tool(tool, **case["input"])
        if request.config.getoption("--record"):
            case_data = {k: v for k, v in case.items() if k != "path"}
            case_data["output"] = output
            case["path"].write_text(
                json.dumps(case_data, indent=2) + "\n", encoding="utf-8"
            )
        elif "output" not in case:
            pytest.skip("no recorded output; run with --record")
        else:
            assert output == case["output"]


@pytest.mark.integration
@pytest.mark.e2e
class TestToolEndToEnd:
    def test_case(self, case: Dict[str, Any], tool: str) -> None:
        output = run_tool(tool, **case["input"])
        assert summarise(output) == case["expected"]
```

The example drives all three kinds from end-to-end case files,
which hold requirements.
Assumption tests written from the external thing's
expected implementation details,
such as an exit code or an ordering,
are separate `integration` tests with their own inputs,
one per assumption, named after it:

```python
@pytest.mark.integration
class TestRunToolAssumptions:
    def test_empty_input_gives_empty_list(self, tool: str) -> None:
        assert run_tool(tool, words=[]) == []
```
