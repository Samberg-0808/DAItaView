## ADDED Requirements

### Requirement: User can connect a database data source
The system SHALL allow users to configure a connection to PostgreSQL, MySQL, or SQLite by providing connection parameters (host, port, database, username, password). Connections SHALL be validated on save.

#### Scenario: Valid database connection saved
- **WHEN** the user submits valid connection parameters for a supported database
- **THEN** the system SHALL test the connection, save it (with the password stored encrypted), and make it available as an active data source

#### Scenario: Invalid connection parameters
- **WHEN** the user submits connection parameters that fail to connect
- **THEN** the system SHALL display a connection error message and not save the configuration

### Requirement: User can upload a file-based data source
The system SHALL allow users to upload CSV, JSON, or Parquet files which are stored locally and queried via DuckDB.

#### Scenario: File upload succeeds
- **WHEN** the user uploads a supported file type (CSV, JSON, Parquet)
- **THEN** the system SHALL store the file, infer its schema, and make it available as an active data source

#### Scenario: Unsupported file type rejected
- **WHEN** the user uploads a file with an unsupported extension
- **THEN** the system SHALL reject the file and display a message listing supported formats

#### Scenario: File exceeds size limit
- **WHEN** the uploaded file exceeds 500MB
- **THEN** the system SHALL reject the upload and display a size limit error

### Requirement: System extracts and caches data source schema
The system SHALL extract table names, column names, data types, and 5 sample rows from each connected data source and cache this schema for use in LLM prompts.

#### Scenario: Schema extracted on connection
- **WHEN** a data source is successfully connected or a file is uploaded
- **THEN** the system SHALL immediately extract and cache the schema

#### Scenario: Schema refresh triggered manually
- **WHEN** the user clicks "Refresh Schema" on a connected data source
- **THEN** the system SHALL re-extract the schema and update the cache

### Requirement: User can switch between multiple active data sources
The system SHALL allow users to have multiple connected data sources and select which one is active for the current query session.

#### Scenario: Active data source switched
- **WHEN** the user selects a different data source from the selector
- **THEN** all subsequent queries SHALL use the newly selected data source's schema and connection
