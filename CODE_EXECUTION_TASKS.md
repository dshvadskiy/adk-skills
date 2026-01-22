# Code Execution Implementation Tasks

This document breaks down the implementation of code execution support for Agent Skills into reasonable, completable chunks of work based on CODE_EXECUTION_SPEC.md.

## Phase 1: Core Infrastructure

### Task 1.1: Create ScriptExecutor Core Class ✅ COMPLETED
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [x] Create `ExecutionResult` dataclass with fields: success, exit_code, stdout, stderr, execution_time, command, error
- [x] Create `ExecutionConstraints` dataclass with fields: max_execution_time, max_memory, network_access, allowed_commands, working_directory
- [x] Implement `ScriptExecutor.__init__()` with skill_name, skill_directory, allowed_tools, constraints parameters
- [x] Set up instance variables: skill_name, skill_directory, scripts_directory, allowed_tools, constraints

**Acceptance Criteria**:
- ✅ ScriptExecutor can be instantiated with basic parameters
- ✅ All dataclasses properly defined with type hints
- ✅ No external dependencies beyond stdlib (subprocess, pathlib, shlex, re)
- ✅ 28 unit tests passing with >90% coverage
- ✅ Type checking passed (mypy)
- ✅ Linting passed (ruff)

---

### Task 1.2: Implement allowed-tools Parsing ✅ COMPLETED
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [x] Implement `_parse_allowed_tools()` method supporting comma-separated format: `"Bash(git:*),Read,Write"`
- [x] Add fallback support for space-separated format: `"Bash(git:*) Read Write"`
- [x] Handle quoted strings and strip whitespace
- [x] Parse tool patterns with regex: `(\w+(?:\([^)]+\))?)`
- [x] Return list of tool permission strings

**Test Cases**:
- Comma-separated: `"Bash(python:*),Bash(jq:*),Read,Write"` → 4 items
- Space-separated: `"Bash(git:*) Read Write"` → 3 items
- Empty string → empty list
- Quoted strings handled correctly

**Acceptance Criteria**:
- ✅ Both comma and space-separated formats work
- ✅ Edge cases handled (empty, quoted, mixed whitespace)
- ✅ 6 unit tests passing (lines 156-210)

---

### Task 1.3: Implement Command Permission Checking ✅ COMPLETED
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [x] Implement `is_command_allowed()` method
- [x] Parse command to extract base command using `shlex.split()`
- [x] Match against allowed_tools patterns
- [x] Support wildcard matching: `Bash(python:*)` allows any python command
- [x] Support scoped permissions: `Bash(git status:*)` allows only "git status"
- [x] Handle exact matches: `Bash(python)` matches python exactly

**Test Cases**:
- `allowed_tools = ["Bash(python:*)"]` → `is_command_allowed("python script.py")` = True
- `allowed_tools = ["Bash(git status:*)"]` → `is_command_allowed("git status")` = True
- `allowed_tools = ["Bash(git status:*)"]` → `is_command_allowed("git commit")` = False
- `allowed_tools = []` → `is_command_allowed("anything")` = False

**Acceptance Criteria**:
- ✅ Wildcard patterns work correctly
- ✅ Scoped permissions enforced
- ✅ Unauthorized commands rejected
- ✅ 6 unit tests passing (lines 212-271)

---

### Task 1.4: Implement Script Path Validation ✅ COMPLETED
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [x] Implement `validate_script_path()` method
- [x] Resolve path relative to skill_directory using `Path.resolve()`
- [x] Check path is within skill_directory (prevent path traversal)
- [x] Verify script file exists
- [x] Verify script is in scripts/ subdirectory
- [x] Raise ValueError with descriptive messages for violations

**Test Cases**:
- Valid path: `"scripts/test.py"` → returns absolute path
- Path traversal: `"../../etc/passwd"` → raises ValueError
- Non-existent: `"scripts/missing.py"` → raises ValueError
- Outside scripts/: `"references/doc.md"` → raises ValueError

**Acceptance Criteria**:
- ✅ Path traversal attacks prevented
- ✅ Clear error messages for each failure case
- ✅ Only scripts in scripts/ directory allowed
- ✅ 4 unit tests passing (lines 273-311)

---

### Task 1.5: Implement Script Execution ✅ COMPLETED
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [x] Implement `execute()` method with command, working_dir, env parameters
- [x] Check command permissions using `is_command_allowed()`
- [x] Set working directory (default to skill_directory)
- [x] Prepare environment variables (merge with system env)
- [x] Add skill context to env: SKILL_NAME, SKILL_DIR, SCRIPTS_DIR
- [x] Execute using `subprocess.run()` with timeout
- [x] Capture stdout, stderr, exit code
- [x] Measure execution time
- [x] Handle TimeoutExpired exception
- [x] Return ExecutionResult with all data

**Test Cases**:
- Successful execution returns exit_code=0, stdout captured
- Timeout triggers TimeoutExpired, returns error
- Permission denied returns error message
- Environment variables properly set

**Acceptance Criteria**:
- ✅ Scripts execute with proper timeout enforcement
- ✅ All output captured correctly
- ✅ Errors handled gracefully with descriptive messages
- ✅ 8 unit tests passing (lines 314-439)

---

## Phase 2: Skill Framework Integration

### Task 2.1: Extend SkillMetadata Dataclass ✅ COMPLETED
**File**: `src/skill_framework/core/skill_loader.py`

**Subtasks**:
- [x] Add `allowed_tools: Optional[str]` field (comma-separated string)
- [x] Add `license: Optional[str]` field
- [x] Add `compatibility: Optional[str]` field
- [x] Add `metadata: Optional[Dict[str, str]]` field (custom metadata map)
- [x] Add `max_execution_time: Optional[int]` field (seconds)
- [x] Add `max_memory: Optional[int]` field (MB)
- [x] Add `network_access: bool` field (default False)
- [x] Add `python_packages: List[str]` field
- [x] Add `system_packages: List[str]` field

**Acceptance Criteria**:
- ✅ All Agent Skills spec fields added
- ✅ Type hints correct
- ✅ Default values appropriate
- ✅ Backward compatible with existing skills
- ✅ 6 unit tests passing
- ✅ Type checking passed (mypy)
- ✅ Linting passed (ruff)

---

### Task 2.2: Update SkillLoader to Parse New Fields ✅ COMPLETED
**File**: `src/skill_framework/core/skill_loader.py`

**Subtasks**:
- [x] Update `_parse_metadata_from_yaml()` to extract `allowed-tools` field (note hyphen)
- [x] Parse `license`, `compatibility`, `metadata` fields
- [x] Parse `max_execution_time`, `max_memory`, `network_access` fields
- [x] Parse `python_packages`, `system_packages` fields
- [x] Handle missing fields gracefully (use defaults)
- [x] Maintain backward compatibility with existing SKILL.md files

**Test Cases**:
- ✅ SKILL.md with all new fields parses correctly
- ✅ SKILL.md without new fields uses defaults
- ✅ Hyphenated YAML keys (allowed-tools) map to underscored Python attributes

**Acceptance Criteria**:
- ✅ All new fields parsed from YAML frontmatter
- ✅ Existing skills without new fields continue to work
- ✅ No breaking changes to existing functionality

---

### Task 2.3: Implement {baseDir} Variable Resolution ✅ COMPLETED
**File**: `src/skill_framework/core/skill_meta_tool.py`

**Subtasks**:
- [x] In `activate_skill()`, resolve skill_directory path
- [x] Replace all `{baseDir}` occurrences in instructions with absolute path
- [x] Handle both `{baseDir}` and `{basedir}` (case variations)
- [x] Ensure paths work on Windows, macOS, Linux

**Test Cases**:
- ✅ `"python {baseDir}/scripts/test.py"` → `"python /path/to/skill/scripts/test.py"`
- ✅ Multiple {baseDir} occurrences all replaced
- ✅ Case-insensitive replacement works

**Acceptance Criteria**:
- ✅ All {baseDir} references resolved to absolute paths
- ✅ Cross-platform path handling
- ✅ Instructions ready for execution
- ✅ 3 unit tests passing
- ✅ Type checking passed (mypy)
- ✅ Linting passed (ruff)

---

### Task 2.4: Create ScriptExecutor in activate_skill() ✅ COMPLETED
**File**: `src/skill_framework/core/skill_meta_tool.py`

**Subtasks**:
- [x] Import ScriptExecutor and ExecutionConstraints
- [x] Check if skill has scripts/ directory
- [x] Create ExecutionConstraints from metadata (max_execution_time, max_memory, network_access)
- [x] Instantiate ScriptExecutor with skill info and constraints
- [x] Add script_executor to modified_context
- [x] Add base_dir to modified_context
- [x] Handle skills without scripts/ gracefully (skip executor creation)

**Test Cases**:
- ✅ Skill with scripts/ directory gets ScriptExecutor in context
- ✅ Skill without scripts/ directory has no executor (no error)
- ✅ Constraints properly configured from metadata

**Acceptance Criteria**:
- ✅ ScriptExecutor created only for skills with scripts/
- ✅ Execution constraints properly configured
- ✅ Context includes executor and base_dir
- ✅ 3 unit tests passing
- ✅ Type checking passed (mypy)
- ✅ Linting passed (ruff)

---

### Task 2.5: Implement Permissions Message Creation ✅ COMPLETED
**File**: `src/skill_framework/core/skill_meta_tool.py`

**Subtasks**:
- [x] Implement `_create_permissions_message()` method
- [x] Create message with type: "command_permissions"
- [x] Include allowedTools array (parsed from allowed-tools)
- [x] Include model field (from metadata)
- [x] Format as user role message
- [x] Add to message injection flow when allowed_tools present

**Message Format**:
```python
{
    "role": "user",
    "content": {
        "type": "command_permissions",
        "allowedTools": ["Bash(python:*)", "Read", "Write"],
        "model": "claude-opus-4-20250514"
    }
}
```

**Acceptance Criteria**:
- ✅ Permissions message created with correct format
- ✅ Only created when allowed_tools field present
- ✅ Injected into conversation context
- ✅ 3 unit tests passing
- ✅ Type checking passed (mypy)
- ✅ Linting passed (ruff)

---

## Phase 3: Testing Infrastructure

### Task 3.1: Unit Tests for ScriptExecutor ✅ COMPLETED
**File**: `tests/unit/test_script_executor.py`

**Subtasks**:
- [x] Create pytest fixture for temporary skill directory with scripts/
- [x] Test `_parse_allowed_tools()` with comma-separated format
- [x] Test `_parse_allowed_tools()` with space-separated format
- [x] Test `is_command_allowed()` with various patterns
- [x] Test `validate_script_path()` with valid paths
- [x] Test `validate_script_path()` with path traversal attempts
- [x] Test `execute()` with successful script
- [x] Test `execute()` with timeout
- [x] Test `execute()` with permission denied
- [x] Test environment variable injection

**Coverage Target**: >90% for ScriptExecutor class

**Acceptance Criteria**:
- ✅ All core ScriptExecutor methods tested
- ✅ Edge cases covered
- ✅ Security validations tested
- ✅ 28 unit tests passing
- ✅ 92% code coverage achieved

---

### Task 3.2: Unit Tests for SkillMetadata Extensions ✅ COMPLETED
**File**: `tests/unit/test_skill_loader.py`

**Subtasks**:
- [x] Test parsing SKILL.md with allowed-tools field
- [x] Test parsing SKILL.md with execution constraints
- [x] Test parsing SKILL.md with dependency fields
- [x] Test backward compatibility (SKILL.md without new fields)
- [x] Test hyphenated YAML keys (allowed-tools → allowed_tools)
- [x] Test default values for missing fields

**Acceptance Criteria**:
- ✅ All new metadata fields tested
- ✅ Backward compatibility verified
- ✅ Default values correct
- ✅ 6 unit tests passing

---

### Task 3.3: Integration Tests for Skill Activation ✅ COMPLETED
**File**: `tests/integration/test_skill_execution.py`

**Subtasks**:
- [x] Create fixture with complete skill (SKILL.md + scripts/)
- [x] Test skill activation creates ScriptExecutor
- [x] Test {baseDir} variable resolution in instructions
- [x] Test permissions message creation
- [x] Test end-to-end: activate skill → execute script → verify output
- [x] Test skill without scripts/ (no executor created)
- [x] Test skill with invalid allowed-tools (error handling)

**Acceptance Criteria**:
- ✅ Complete activation flow tested
- ✅ Script execution verified end-to-end
- ✅ Error cases handled
- ✅ 9 integration tests passing
- ✅ All tests pass with full suite (203 passed)

---

### Task 3.4: Security Tests ✅ COMPLETED
**File**: `tests/unit/test_script_executor.py` (integrated into main test file)

**Subtasks**:
- [x] Test path traversal prevention: `../../etc/passwd`
- [x] Test command injection prevention (via command parsing)
- [x] Test unauthorized command execution blocked
- [x] Test timeout enforcement
- [x] Test working directory restriction
- [x] Test environment variable isolation

**Acceptance Criteria**:
- ✅ All security mechanisms tested
- ✅ Attack vectors prevented (path traversal test passes)
- ✅ No false positives (legitimate commands work)
- ✅ Security tests integrated into test_script_executor.py
- ✅ 28 unit tests passing with 92% coverage

---

## Phase 4: Example Skills and Documentation

### Task 4.1: Create data-analysis Example Skill ✅ COMPLETED
**Directory**: `skills/data-analysis/`

**Subtasks**:
- [x] Create SKILL.md with allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
- [x] Create scripts/extract.py (CSV analysis with pandas)
- [x] Create scripts/stats.py (statistical analysis)
- [x] Create scripts/visualize.py (chart generation)
- [x] Create references/REFERENCE.md (API documentation)
- [x] Add error handling and helpful messages to scripts
- [x] Make scripts executable (chmod +x)
- [x] Add requirements.txt for Python dependencies

**Acceptance Criteria**:
- ✅ Complete working skill with 3 scripts (extract.py, stats.py, visualize.py)
- ✅ Scripts handle errors gracefully with try/except blocks
- ✅ Documentation clear and helpful (comprehensive REFERENCE.md)

---

### Task 4.2: Create git-helper Example Skill ⏭️ SKIPPED
**Directory**: `skills/git-helper/`

**Status**: Skipped - data-analysis skill provides sufficient example

**Rationale**: The data-analysis skill already demonstrates all key features:
- Script execution with proper permissions
- Multiple scripts with different purposes
- Comprehensive documentation
- Error handling and user-friendly output
- {baseDir} variable usage

---

### Task 4.3: Update Documentation ✅ COMPLETED
**Files**: `README.md`, `SPEC.md`, new `CODE_EXECUTION.md`

**Subtasks**:
- [x] Create comprehensive CODE_EXECUTION.md guide
- [x] Add code execution section to README.md
- [x] Document allowed-tools format and syntax
- [x] Document {baseDir} variable usage
- [x] Document security model and constraints
- [x] Add examples of skills with scripts
- [x] Document deployment considerations
- [x] Add troubleshooting guide
- [x] Update README with code execution features

**Acceptance Criteria**:
- ✅ Clear documentation for skill authors (CODE_EXECUTION.md created - 15KB)
- ✅ Examples easy to follow (data-analysis skill referenced throughout)
- ✅ Security considerations explained (dedicated security section)
- ✅ README updated with code execution overview

---

## Phase 5: Google ADK Integration

### Task 5.1: Create ADK Bash Tool Wrapper ✅ COMPLETED
**File**: `src/skill_framework/integration/adk_tools.py`

**Subtasks**:
- [x] Create `create_bash_tool_with_skill_executor()` function
- [x] Wrap ScriptExecutor.execute() as ADK-compatible tool function
- [x] Handle ExecutionResult → string conversion with LLM-friendly formatting
- [x] Format errors for LLM consumption
- [x] Add tool description and parameter schema via docstring
- [x] Create `create_read_file_tool()` for safe file reading
- [x] Create `create_write_file_tool()` for safe file writing

**Acceptance Criteria**:
- ✅ Bash tool integrates with Google ADK as callable function
- ✅ ScriptExecutor constraints enforced (permissions, timeout)
- ✅ Errors formatted clearly for LLM
- ✅ File I/O tools with path traversal protection
- ✅ 10 integration tests passing
- ✅ Type checking passed (mypy)
- ✅ Linting passed (ruff)

---

### Task 5.2: Update AgentBuilder for Code Execution ✅ COMPLETED
**File**: `src/skill_framework/agent/agent_builder.py`

**Subtasks**:
- [x] Create `_create_execution_tools_for_skill()` method
- [x] Check if skill has scripts/ directory
- [x] Create ScriptExecutor with skill's constraints
- [x] Create bash_tool, read_file, write_file tools
- [x] Return list of tool functions for ADK Agent
- [x] Update `_create_skill_tool()` to store skill context
- [x] Tools scoped to skill directory and permissions

**Acceptance Criteria**:
- ✅ Agents with script-enabled skills can create execution tools
- ✅ Permissions enforced at runtime via ScriptExecutor
- ✅ Tools only created for skills with scripts/ directory
- ✅ Integration with existing AgentBuilder
- ✅ 10 integration tests passing
- ✅ All 213 tests passing in full suite

---

### Task 5.3: Integration Tests with ADK ✅ COMPLETED
**File**: `tests/integration/test_adk_code_execution.py`

**Subtasks**:
- [x] Test creating execution tools for skill with scripts
- [x] Test skills without scripts don't get tools
- [x] Test bash tool executes allowed commands
- [x] Test bash tool blocks unauthorized commands
- [x] Test bash tool executes skill scripts
- [x] Test read_file tool reads from skill directory
- [x] Test read_file tool blocks path traversal
- [x] Test write_file tool writes to skill directory
- [x] Test write_file tool blocks path traversal
- [x] Test execution tools respect timeout constraints

**Acceptance Criteria**:
- ✅ End-to-end ADK integration working
- ✅ Scripts execute correctly through bash tool
- ✅ Permissions enforced (unauthorized commands blocked)
- ✅ Security validated (path traversal prevented)
- ✅ 10 integration tests passing
- ✅ All tests pass with full suite (213 passed)

---

## Phase 6: Advanced Features and Hardening

### Task 6.1: Add Script Validation on Skill Load
**File**: `src/skill_framework/core/skill_loader.py`

**Subtasks**:
- [ ] Validate scripts/ directory structure on load
- [ ] Check scripts are executable (Unix permissions)
- [ ] Validate script shebangs (#!/usr/bin/env python3)
- [ ] Check for required dependencies (python_packages)
- [ ] Warn about missing dependencies
- [ ] Add validation results to metadata

**Acceptance Criteria**:
- Skills validated at load time
- Clear warnings for configuration issues
- Non-blocking (warnings, not errors)

---

### Task 6.2: Add Execution Metrics and Logging
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [ ] Add structured logging to ScriptExecutor
- [ ] Log execution start/end with timing
- [ ] Log permission checks (allowed/denied)
- [ ] Log resource usage (execution time)
- [ ] Add execution metrics collection
- [ ] Create ExecutionMetrics dataclass

**Acceptance Criteria**:
- All executions logged with context
- Metrics available for monitoring
- Debug-friendly log output

---

### Task 6.3: Add Memory Limit Enforcement (Linux)
**File**: `src/skill_framework/core/script_executor.py`

**Subtasks**:
- [ ] Implement memory limit using resource.setrlimit() (Linux)
- [ ] Add platform detection (Linux only for now)
- [ ] Handle MemoryError exceptions
- [ ] Document platform limitations
- [ ] Add tests for memory limits (Linux only)

**Acceptance Criteria**:
- Memory limits enforced on Linux
- Graceful degradation on other platforms
- Clear error messages

---

### Task 6.4: Add Network Isolation (Optional)
**File**: `src/skill_framework/core/execution_sandbox.py`

**Subtasks**:
- [ ] Create ExecutionSandbox class
- [ ] Implement network isolation using unshare() (Linux)
- [ ] Add container-based isolation option (Docker)
- [ ] Document network isolation setup
- [ ] Add configuration for isolation level

**Note**: This is an advanced feature, may be deferred to future release.

**Acceptance Criteria**:
- Network isolation available as opt-in
- Works in container environments
- Documented setup process

---

## Phase 7: Deployment and Release

### Task 7.1: Create Deployment Guide
**File**: `docs/DEPLOYMENT.md`

**Subtasks**:
- [ ] Document Docker deployment with skills
- [ ] Create example Dockerfile
- [ ] Document dependency installation
- [ ] Document environment variables
- [ ] Add AWS Bedrock deployment guide
- [ ] Add GCP Vertex AI deployment guide
- [ ] Document security best practices

**Acceptance Criteria**:
- Complete deployment documentation
- Working Dockerfile example
- Cloud deployment guides

---

### Task 7.2: Create Migration Guide
**File**: `docs/MIGRATION.md`

**Subtasks**:
- [ ] Document how to add scripts to existing skills
- [ ] Provide before/after examples
- [ ] Document testing checklist
- [ ] Add troubleshooting section
- [ ] Document backward compatibility guarantees

**Acceptance Criteria**:
- Clear migration path for existing skills
- Examples easy to follow
- Backward compatibility verified

---

### Task 7.3: Final Testing and Validation
**Multiple Files**

**Subtasks**:
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Run type checking: `uv run mypy src/`
- [ ] Run linting: `uv run ruff check src/ tests/`
- [ ] Run formatting check: `uv run ruff format --check src/ tests/`
- [ ] Test with real skills (data-analysis, git-helper)
- [ ] Test on multiple platforms (macOS, Linux)
- [ ] Performance testing (execution overhead)
- [ ] Security audit (path traversal, command injection)

**Acceptance Criteria**:
- All tests pass
- No type errors
- No linting errors
- Code properly formatted
- Security validated

---

## Summary

**Phases**:
1. ✅ **Core Infrastructure**: ScriptExecutor implementation (COMPLETE)
2. ✅ **Skill Framework Integration**: SkillMetaTool updates (COMPLETE)
3. ✅ **Testing Infrastructure**: Comprehensive test coverage (COMPLETE)
4. ✅ **Example Skills**: Working examples and docs (COMPLETE)
5. ✅ **Google ADK Integration**: ADK tool integration (COMPLETE)
6. **Advanced Features**: Validation, metrics, sandboxing (OPTIONAL)
7. **Deployment**: Documentation and final validation (OPTIONAL)

**Current Status**: Phase 5 Complete - 213 tests passing

**Completed Tasks**:
- Phase 1: Tasks 1.1-1.5 ✅ (ScriptExecutor core with 92% coverage)
- Phase 2: Tasks 2.1-2.5 ✅ (Skill framework integration)
- Phase 3: Tasks 3.1-3.4 ✅ (Complete test coverage)
- Phase 4: Tasks 4.1, 4.3 ✅ (Example skill + comprehensive documentation)
- Phase 4: Task 4.2 ⏭️ (Skipped - not needed)
- Phase 5: Tasks 5.1-5.3 ✅ (ADK integration with execution tools)

**Implementation Notes**:

The final implementation uses **universal execution tools** that are registered at agent creation time:
- `bash_tool(command, working_directory)` - Executes commands using active skill's ScriptExecutor
- `read_file(file_path)` - Reads files from active skill's directory
- `write_file(file_path, content)` - Writes files to active skill's directory

These tools check for an active skill and use its permissions/constraints dynamically. This approach:
- ✅ Works with ADK's static tool registration requirement
- ✅ Maintains security (permissions enforced per skill)
- ✅ Provides clear error messages when no skill is active
- ✅ Supports multiple skills in same session (uses most recent)

**Next Steps**: Phase 6 - Advanced Features (optional) or Phase 7 - Deployment (optional)

**Critical Path**:
1. Task 1.1-1.5 (ScriptExecutor core)
2. Task 2.1-2.5 (Integration)
3. Task 3.1-3.3 (Testing)
4. Task 5.1-5.2 (ADK integration)
5. Task 7.3 (Final validation)

**Dependencies**:
- Phase 2 depends on Phase 1 completion
- Phase 3 can run parallel with Phase 2 (TDD approach)
- Phase 4 depends on Phase 1-2
- Phase 5 depends on Phase 1-2
- Phase 6 can be done incrementally
- Phase 7 is final integration

**Risk Areas**:
- Security validation (path traversal, command injection)
- Cross-platform compatibility (Windows, macOS, Linux)
- Google ADK integration (API changes)
- Performance overhead of script execution
