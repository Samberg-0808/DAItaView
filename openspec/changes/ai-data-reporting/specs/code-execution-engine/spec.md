## ADDED Requirements

### Requirement: Code is executed in a sandboxed subprocess
The system SHALL execute all generated code in a separate subprocess with restricted builtins (via RestrictedPython), no network access, and enforced resource limits (CPU time and memory).

#### Scenario: Code executes successfully
- **WHEN** valid, safe code is submitted for execution
- **THEN** the system SHALL run the code in an isolated subprocess and return the result (a Plotly chart JSON or a tabular dataset)

#### Scenario: Execution exceeds time limit
- **WHEN** code execution takes longer than 30 seconds
- **THEN** the system SHALL terminate the subprocess and return a timeout error to the caller

#### Scenario: Memory limit exceeded
- **WHEN** the subprocess exceeds the 512MB memory limit
- **THEN** the system SHALL terminate it and return an out-of-memory error to the caller

### Requirement: Execution result is returned as a structured payload
The system SHALL return execution results as a JSON payload containing: result type (`chart` or `table`), data (Plotly figure JSON or row/column data), and any execution warnings.

#### Scenario: Chart result returned
- **WHEN** the executed code produces a Plotly figure
- **THEN** the execution engine SHALL serialize it to JSON and return it with `type: "chart"`

#### Scenario: Table result returned
- **WHEN** the executed code produces a pandas DataFrame
- **THEN** the execution engine SHALL convert it to a list of row dicts and return it with `type: "table"`, including column names and up to 1000 rows

#### Scenario: No output produced
- **WHEN** the executed code runs without error but produces no figure or DataFrame
- **THEN** the system SHALL return a warning message: "Code ran successfully but produced no output."

### Requirement: Only an allowlisted set of Python imports is permitted
The system SHALL maintain an allowlist of safe imports (`pandas`, `numpy`, `duckdb`, `plotly`, `datetime`, `math`, `json`, `re`, `collections`) and block all others at the RestrictedPython level.

#### Scenario: Allowlisted import succeeds
- **WHEN** generated code imports `pandas` or another allowlisted library
- **THEN** the import SHALL succeed and execution continues normally

#### Scenario: Blocked import attempted
- **WHEN** generated code attempts to import a non-allowlisted module
- **THEN** the execution engine SHALL raise an ImportError and return it as an execution error without running any code
