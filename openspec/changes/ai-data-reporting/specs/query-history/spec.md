## ADDED Requirements

### Requirement: All queries and results are persisted to history
The system SHALL automatically save every completed query (question, generated code, result payload, data source name, timestamp, and status) to a local persistent store after execution completes.

#### Scenario: Successful query saved to history
- **WHEN** a query completes successfully
- **THEN** the system SHALL persist the question, code, result, data source name, and completion timestamp

#### Scenario: Failed query saved to history
- **WHEN** a query fails after all retries
- **THEN** the system SHALL persist the question, the last generated code, the error message, and status `failed`

### Requirement: User can browse query history
The system SHALL provide a history panel showing past queries in reverse chronological order, displaying the question text, data source, timestamp, and status (success/failed).

#### Scenario: History panel shows past queries
- **WHEN** the user opens the history panel
- **THEN** the system SHALL display all past queries with their question preview, data source name, relative timestamp, and success/failure status

#### Scenario: Empty history state
- **WHEN** no queries have been run yet
- **THEN** the history panel SHALL display an empty-state message: "No queries yet. Ask your first question above."

### Requirement: User can replay a past query
The system SHALL allow users to re-run a past query from history, which re-executes the original question against the current state of the data source.

#### Scenario: Replay a past query
- **WHEN** the user clicks "Replay" on a history entry
- **THEN** the system SHALL submit the original question as a new query and display the result in the main chat view

### Requirement: User can delete individual history entries or clear all history
The system SHALL allow users to delete individual history records or clear the entire history.

#### Scenario: Delete single history entry
- **WHEN** the user clicks "Delete" on a history entry and confirms
- **THEN** that entry SHALL be removed from the history store and no longer visible

#### Scenario: Clear all history
- **WHEN** the user clicks "Clear All History" and confirms the prompt
- **THEN** all history entries SHALL be deleted from the store
