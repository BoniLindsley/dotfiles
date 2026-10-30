# C++ with Catch2 and CTest

Mechanics for the external-boundaries skill with Catch2 and CTest.
Read `../SKILL.md` first.
The example was not compiled.

- Tag tests that need the external thing `[integration]`,
  and end-to-end tests also `[e2e]`.
  Unit tests have neither tag.
- `"~[integration]"` runs the unit tests only;
  `"[e2e]"` confirms the hard-coded cases.
  Pass tags to CTest as labels (Catch2 3.8 or later),
  so that `ctest -LE integration` does the same.
- Skip with `SKIP("reason")` (Catch2 3.3 or later)
  when the external thing is missing.
- Store cases as data files next to the tests,
  give their directory to the tests as a compile definition,
  and iterate over them with `GENERATE`.
  Find large data through an environment variable,
  and skip when it is not set.
- Rewrite recorded outputs from the external thing
  only when an environment variable such as `RECORD_CASES` is set.
- The example drives all three kinds from end-to-end case files.
  Assumption tests written from the external thing's
  expected implementation details have their own inputs,
  one `[integration]` test per assumption, named after it.

```cmake
target_compile_definitions(tests PRIVATE
  CASES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/cases")
catch_discover_tests(tests ADD_TAGS_AS_LABELS)
```

```cpp
// Case files, find_tool_or_skip() and run_tool() are defined elsewhere;
// find_tool_or_skip() calls SKIP() when the tool is not found.

TEST_CASE("summarise gives the expected result", "[summarise]")
{
    auto const path = GENERATE(from_range(case_paths(CASES_DIR)));
    auto const tool_case = load_case(path);
    if (not tool_case.output)
    {
        SKIP("no recorded output; set RECORD_CASES=1");
    }
    CHECK(summarise(*tool_case.output) == tool_case.expected);
}

TEST_CASE("run_tool gives the recorded output", "[run_tool][integration]")
{
    auto const tool = find_tool_or_skip();
    auto const path = GENERATE(from_range(case_paths(CASES_DIR)));
    auto tool_case = load_case(path);
    auto const output = run_tool(tool, tool_case.input);
    if (recording())
    {
        tool_case.output = output;
        save_case(path, tool_case);
    }
    else if (not tool_case.output)
    {
        SKIP("no recorded output; set RECORD_CASES=1");
    }
    else
    {
        CHECK(output == *tool_case.output);
    }
}

TEST_CASE("tool cases end to end", "[integration][e2e]")
{
    auto const tool = find_tool_or_skip();
    auto const path = GENERATE(from_range(case_paths(CASES_DIR)));
    auto const tool_case = load_case(path);
    CHECK(summarise(run_tool(tool, tool_case.input)) == tool_case.expected);
}
```
