## ADDED Requirements

### Requirement: System generates executable code from a natural language question
The system SHALL call the Claude API with the user's question, the active data source schema (filtered by user permissions), the knowledge curriculum context, and the session's question history to produce executable Python (pandas + DuckDB) or SQL code that answers the question.

#### Scenario: Successful code generation
- **WHEN** a valid question, a connected data source, and an active session are provided
- **THEN** the system SHALL return a clean, executable code string and the detected output type (table or chart)

#### Scenario: No data source connected
- **WHEN** a question is submitted but no data source is active for the session
- **THEN** the system SHALL return an error message instructing the user to start a new session with a connected data source

### Requirement: LLM prompt includes question history but never result data
The system SHALL pass the full ordered list of prior questions from the current session into the LLM prompt to support follow-up queries. Result data, generated code, and chart payloads SHALL never be included in the LLM context.

#### Scenario: Follow-up question resolves against prior questions
- **WHEN** the user asks a follow-up such as "now break that down by region"
- **THEN** the prompt SHALL include all prior questions in the session so the LLM can resolve "that" from question history

#### Scenario: Clarification answers included in history
- **WHEN** a prior turn included clarification Q&A
- **THEN** the clarification questions and the user's answers SHALL be included in that turn's history entry, so the LLM carries forward any definitions established (e.g., "premium = tier='premium'")

#### Scenario: Result data is never sent to LLM
- **WHEN** building the LLM prompt for any turn
- **THEN** the system SHALL include only question text and clarification answers from prior turns — no chart JSON, no table rows, no execution output

### Requirement: Long session history is summarised to stay within context budget
When the total token count of the full question history exceeds 10k tokens, the system SHALL summarise the oldest turns into a paragraph and retain the most recent 10 turns verbatim.

#### Scenario: History within budget
- **WHEN** the session has few enough turns that full question history fits within 10k tokens
- **THEN** all prior questions SHALL be passed verbatim in order

#### Scenario: History exceeds budget
- **WHEN** the full question history exceeds 10k tokens
- **THEN** the system SHALL summarise the oldest turns into a brief paragraph ("Earlier in this session the user explored X, Y, and Z") and append the last 10 questions verbatim after the summary

### Requirement: Schema context is filtered by user permissions before injection
The system SHALL only include tables the requesting user is permitted to access when building the schema section of the LLM prompt. Restricted tables SHALL be omitted entirely — not listed as inaccessible.

#### Scenario: Schema filtered to permitted tables only
- **WHEN** generating a prompt for a user who cannot access certain tables
- **THEN** the schema injected into the prompt SHALL contain only the tables the user is permitted to query; restricted tables SHALL not appear at all

### Requirement: Knowledge curriculum is injected using a dynamic context budget strategy
The system SHALL select a knowledge injection strategy based on the estimated token size of the full relevant knowledge base for the active source.

#### Scenario: Small knowledge base — full injection
- **WHEN** the estimated token count of all relevant knowledge layers is under 20k tokens
- **THEN** all relevant layers (global, source, matched domains, matched table annotations, matched examples) SHALL be injected in a single prompt

#### Scenario: Medium knowledge base — semantic RAG
- **WHEN** the estimated token count is between 20k and 80k tokens
- **THEN** the system SHALL embed the question, retrieve the top-K most similar knowledge chunks, and include all table annotations for tables matched by keyword — in a single prompt

#### Scenario: Large knowledge base — multi-pass agentic
- **WHEN** the estimated token count exceeds 80k tokens
- **THEN** Pass 1 SHALL send global + source-level knowledge + domain summaries to the LLM to identify the needed tables and domains; Pass 2 SHALL fetch the detailed annotations and examples for those specifics and generate code

### Requirement: LLM executes a thinking phase before generating code
Before producing executable code, the LLM SHALL output a structured reasoning step identifying relevant tables, applicable business rules, and any ambiguities it cannot resolve from the knowledge base.

#### Scenario: Thinking phase produced before code
- **WHEN** the LLM receives a question with sufficient knowledge context
- **THEN** it SHALL first emit a reasoning block, then the executable code

#### Scenario: Ambiguity detected during thinking
- **WHEN** the thinking phase reveals that answering the question requires information not present in the knowledge base or question history
- **THEN** the LLM SHALL emit structured clarification questions instead of code, and the pipeline SHALL pause until the user responds

#### Scenario: Clarification only asked when answer would materially change the code
- **WHEN** the LLM detects an ambiguity that is minor or resolvable by a reasonable default assumption
- **THEN** it SHALL proceed with code generation, stating its assumption explicitly in the thinking block, rather than asking a clarification question

### Requirement: Generation errors trigger automatic retry with error context
The system SHALL retry code generation up to 2 times when the generated code fails to execute, appending the execution error to the prompt so the LLM can self-correct.

#### Scenario: First execution fails, retry succeeds
- **WHEN** the generated code raises an exception during execution
- **THEN** the system SHALL re-call the Claude API with the original question, schema, prior code, and the error message, and attempt execution again

#### Scenario: All retries exhausted
- **WHEN** generated code fails on all 3 attempts (initial + 2 retries)
- **THEN** the system SHALL return the last error message to the user and stop retrying

### Requirement: Generated code is validated against permitted tables before execution
After code generation and before execution, the system SHALL parse the generated code for table references and reject it if any referenced table is not in the user's permitted table list.

#### Scenario: Permitted tables only — execution proceeds
- **WHEN** all table references in the generated code are within the user's permitted set
- **THEN** the code is passed to the execution engine

#### Scenario: Restricted table referenced — execution blocked
- **WHEN** the generated code references a table the user cannot access
- **THEN** the system SHALL reject the code without executing it, log the violation to the audit log, and return a safe error message to the user

### Requirement: Generated code is sanitized for dangerous patterns before execution
The system SHALL scan generated code for dangerous patterns (e.g., `os`, `sys`, `subprocess`, `eval`, `exec`, `open`, `__import__`) and reject it without executing if any are found.

#### Scenario: Dangerous import detected
- **WHEN** the LLM generates code containing a blocked pattern
- **THEN** the system SHALL reject the code, log the violation, and return a safe error message to the user without executing the code
