## ADDED Requirements

### Requirement: User can submit natural language queries
The system SHALL provide a chat-style text input where users can type plain-English questions about their data. Questions are submitted by pressing Enter or clicking a Send button.

#### Scenario: Submit a query
- **WHEN** the user types a question and presses Enter
- **THEN** the system SHALL send the question to the backend and display a loading indicator

#### Scenario: Empty query prevented
- **WHEN** the user attempts to submit an empty or whitespace-only message
- **THEN** the system SHALL do nothing and keep focus on the input field

### Requirement: Query pipeline status is shown in real time
The system SHALL display live status updates as the query progresses through the pipeline stages: queued, generating code, executing, and rendering.

#### Scenario: Status progression displayed
- **WHEN** a query is submitted and in progress
- **THEN** the UI SHALL show the current stage label and a spinner until results are ready

#### Scenario: Error state displayed
- **WHEN** the backend returns an error (e.g., execution failure, LLM error)
- **THEN** the UI SHALL display a human-readable error message and offer a retry option

### Requirement: Generated code is shown to the user
The system SHALL display the LLM-generated code alongside the result so users can inspect, understand, and copy it.

#### Scenario: Code collapsed by default after first turn
- **WHEN** a query completes in the first turn of a session
- **THEN** the UI SHALL show the code block expanded by default

#### Scenario: Code collapsed on subsequent turns
- **WHEN** a query completes in turn 2 or later
- **THEN** the UI SHALL show the code block collapsed by default to reduce noise; the user can expand it

#### Scenario: User copies generated code
- **WHEN** the user clicks the copy button on the code block
- **THEN** the system SHALL copy the code to the clipboard and show a brief confirmation

### Requirement: Sessions are managed via a sidebar
The system SHALL provide a sidebar listing all of the user's chat sessions grouped by recency (Today, Yesterday, Last 7 days, Older), with options to create, rename, pin, and delete sessions.

#### Scenario: Session list displayed
- **WHEN** the user opens the application
- **THEN** the sidebar SHALL display all sessions grouped chronologically with title, data source name, and relative timestamp

#### Scenario: Session auto-titled from first question
- **WHEN** a new session's first query completes
- **THEN** the session title SHALL be set automatically from the first question text (truncated to 50 characters)

#### Scenario: User renames a session
- **WHEN** the user double-clicks a session title or selects rename from the context menu
- **THEN** the title SHALL become an inline editable field; the new title is saved on blur or Enter

#### Scenario: User pins a session
- **WHEN** the user clicks the pin option on a session
- **THEN** the session SHALL appear at the top of the sidebar above all date groups and persist there across logins

#### Scenario: User deletes a session
- **WHEN** the user selects delete from the session context menu and confirms the prompt
- **THEN** the session and all its turns SHALL be permanently removed

### Requirement: New session requires selecting a data source
The system SHALL prompt the user to select a data source when creating a new chat session. The selected source is locked for the lifetime of the session and cannot be changed.

#### Scenario: New chat source picker shown
- **WHEN** the user clicks "+ New Chat"
- **THEN** the system SHALL display a modal listing the data sources the user has permission to access

#### Scenario: Session locked to selected source
- **WHEN** the user selects a source and starts chatting
- **THEN** the active data source SHALL be displayed persistently in the session header and cannot be changed within that session

#### Scenario: No accessible sources
- **WHEN** the user clicks "+ New Chat" but has no permitted data sources
- **THEN** the system SHALL display a message: "You don't have access to any data sources. Contact your admin."

### Requirement: Results show a data staleness indicator
Every query result SHALL display a timestamp showing when its data was last fetched, and a Refresh button to re-execute the stored code against the current data.

#### Scenario: Staleness badge shown on result
- **WHEN** a result is displayed (on first execution or session re-open)
- **THEN** each result card SHALL show "Last updated: [timestamp]" and a Refresh button

#### Scenario: Session opened with old results
- **WHEN** a user opens a session where the most recent result is older than 1 hour
- **THEN** a banner SHALL appear at the top of the chat: "Results in this session are from [X] hours ago. Refresh all?"

#### Scenario: User refreshes a single result
- **WHEN** the user clicks Refresh on a result card
- **THEN** the system SHALL re-execute the stored code against the current data, update the result, and update the timestamp — without making a new LLM call

#### Scenario: User refreshes all results in a session
- **WHEN** the user clicks "Refresh all" in the staleness banner
- **THEN** the system SHALL re-execute the stored code for every turn in the session sequentially

### Requirement: Result refresh handles schema change errors gracefully
If re-executing stored code fails because the data source schema has changed, the system SHALL show a specific error state with recovery options.

#### Scenario: Refresh fails due to schema change
- **WHEN** a result refresh fails with a column-not-found or table-not-found error
- **THEN** the result card SHALL display an error state with the specific error message, a "View original result" option to restore the cached output, and a "Re-ask this question" option that re-runs the full pipeline (LLM → code → execute) with the current schema

### Requirement: LLM thinking phase is displayed per turn
The system SHALL show the LLM's reasoning step before the result, allowing users to verify the system understood the question correctly.

#### Scenario: Thinking shown expanded on first turn
- **WHEN** the first query in a session completes
- **THEN** the thinking block SHALL be displayed expanded by default

#### Scenario: Thinking collapsed on subsequent turns
- **WHEN** a query in turn 2 or later completes
- **THEN** the thinking block SHALL be collapsed by default; the user can expand it

### Requirement: Structured clarification questions are displayed inline
When the LLM cannot proceed with sufficient confidence, it SHALL display structured clarification questions inline in the chat rather than attempting to generate code.

#### Scenario: Clarification presented before code generation
- **WHEN** the LLM's thinking phase identifies ambiguity that would materially change the generated code
- **THEN** the system SHALL display the clarification questions inline with selectable options or a text input, and NOT generate code until the user responds

#### Scenario: User answers clarification and query proceeds
- **WHEN** the user submits answers to all clarification questions
- **THEN** the system SHALL resume the pipeline and generate code using the original question plus the clarification answers
