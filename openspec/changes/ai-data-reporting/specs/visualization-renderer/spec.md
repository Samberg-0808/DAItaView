## ADDED Requirements

### Requirement: System auto-selects an appropriate chart type based on result shape
The system SHALL analyze the shape of the query result (number of columns, data types, cardinality) and select the most appropriate visualization type (bar, line, scatter, pie, or table) when the LLM does not explicitly specify one.

#### Scenario: Single numeric column with categorical axis
- **WHEN** the result has one categorical column and one numeric column
- **THEN** the system SHALL render a bar chart by default

#### Scenario: Two numeric columns with a date/time axis
- **WHEN** the result has a date/time column and one or more numeric columns
- **THEN** the system SHALL render a line chart by default

#### Scenario: More than 2 numeric columns or complex shape
- **WHEN** the result has 3+ columns or no clear chart mapping
- **THEN** the system SHALL fall back to rendering a table

#### Scenario: LLM explicitly specifies chart type
- **WHEN** the generated code explicitly creates a named Plotly figure type
- **THEN** the system SHALL use that chart type without overriding it

### Requirement: Charts are rendered interactively in the frontend
The system SHALL render Plotly charts using `react-plotly.js` with pan, zoom, hover tooltips, and PNG download enabled by default.

#### Scenario: Chart renders from JSON payload
- **WHEN** the frontend receives a `type: "chart"` result payload
- **THEN** it SHALL render the Plotly figure using `react-plotly.js` with default interactive controls

#### Scenario: User downloads chart as PNG
- **WHEN** the user clicks the download button on a rendered chart
- **THEN** the system SHALL trigger a Plotly PNG export of the current chart view

### Requirement: Table results are rendered as a paginated data grid
The system SHALL render tabular results as a sortable, paginated data grid with up to 50 rows per page and column header sorting.

#### Scenario: Table rendered with pagination
- **WHEN** the frontend receives a `type: "table"` result payload with more than 50 rows
- **THEN** it SHALL render the first 50 rows and show pagination controls

#### Scenario: Column header sort
- **WHEN** the user clicks a column header in the data grid
- **THEN** the rows SHALL be sorted by that column (ascending on first click, descending on second)

### Requirement: Visualization result can be exported as CSV
The system SHALL allow users to download the raw data behind any result (chart or table) as a CSV file.

#### Scenario: CSV export from chart result
- **WHEN** the user clicks "Export CSV" on a chart result
- **THEN** the system SHALL download the underlying data as a CSV file with proper column headers
