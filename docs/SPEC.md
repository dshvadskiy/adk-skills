Skills Meta-Tool Architecture: Complete Specification & Skeleton Project
Executive Summary
This specification defines a production implementation of the Skills meta-tool architecture following Claude Code's design pattern. The implementation enables progressive disclosure, two-message injection, dynamic permission scoping, and LLM-based skill selection.

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| SkillLoader | ✅ Complete | Parses SKILL.md, returns SkillMetadata/SkillContent |
| SkillMetadata | ✅ Complete | Dataclass with all frontmatter fields |
| SkillContent | ✅ Complete | Dataclass for full skill content |
| SkillMetaTool | ✅ Complete | Core meta-tool orchestration (27 tests) |
| MessageInjector | ✅ Complete | Two-message pattern (26 tests) |
| ContextManager | ✅ Complete | Execution context modification (17 tests) |
| PermissionManager | ✅ Complete | Tool permission scoping (21 tests) |
| AgentBuilder | ✅ Complete | Google ADK integration (31 tests) |
| ConversationManager | ✅ Complete | Conversation state management (30 tests) |
| ToolRegistry | ✅ Complete | Tool management (14 tests) |
| ADKAdapter | ✅ Complete | Google ADK adapter (13 tests passing) |
| Integration Tests | ✅ Complete | End-to-end + ADK integration (25 tests) |
| Skills | ✅ Dynamic | Auto-discovered from skills/ directory |

Table of Contents

Architecture Specification
Project Structure
Core Components
Implementation Skeleton
Testing Framework
Deployment Guide


1. Architecture Specification
1.1 Design Principles
yamlprinciples:
  progressive_disclosure:
    description: "Load skill content only when needed"
    rationale: "Minimize context window usage"
    implementation: "Meta-tool reads SKILL.md on-demand via bash"
  
  two_message_pattern:
    description: "Inject visible metadata + hidden instructions"
    rationale: "Separate user-facing UI from LLM context"
    messages:
      - type: "command-message"
        visible: true
        purpose: "User feedback"
      - type: "skill-instructions"
        visible: false
        isMeta: true
        purpose: "LLM context"
  
  dynamic_permissions:
    description: "Modify tool access per skill"
    rationale: "Security and appropriate capability scoping"
    scope: "execution-context"
  
  llm_selection:
    description: "Let LLM decide which skill to use"
    rationale: "More flexible than algorithmic matching"
    method: "Tool description matching"
```

### 1.2 Component Architecture
```
┌─────────────────────────────────────────────────────────────┐
│ System Prompt                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Base Instructions                                        │ │
│ │ Available Skills: [metadata only]                       │ │
│ │   - fraud-analysis: Detect fraud patterns               │ │
│ │   - report-gen: Create reports                          │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Tools Array                                                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Skill (meta-tool)                                        │ │
│ │   description: "Activate specialized skill"             │ │
│ │   parameters: {skill_name: string}                      │ │
│ │ bash_tool                                                │ │
│ │ file_operations                                          │ │
│ │ python_execute                                           │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
                User: "Analyze fraud.csv"
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM Decision Making                                          │
│ "I need fraud analysis skill for this task"                 │
│ → toolUse: {name: "Skill", input: {skill_name: "fraud"}}   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Skill Meta-Tool Execution                                    │
│ 1. Read /skills/fraud-analysis/SKILL.md (bash)             │
│ 2. Inject Message 1: <command-message>                      │
│ 3. Inject Message 2 (isMeta=true): [full content]          │
│ 4. Modify context: {allowed_tools: [...]}                  │
│ 5. Return control to LLM                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM Continues with Skill Context                            │
│ - Has full skill instructions in context                    │
│ - Can access permitted tools                                │
│ - Executes task following skill guidelines                  │
└─────────────────────────────────────────────────────────────┘
1.3 Message Flow Specification
python# Message Flow State Machine

class MessageFlowState:
    """
    Defines the state transitions in skill-augmented conversation.
    """
    
    STATES = {
        'INITIAL': {
            'messages': ['user_query'],
            'context': 'default',
            'transitions': ['SKILL_SELECTION', 'DIRECT_RESPONSE']
        },
        
        'SKILL_SELECTION': {
            'messages': ['tool_use: Skill'],
            'context': 'default',
            'transitions': ['SKILL_LOADING']
        },
        
        'SKILL_LOADING': {
            'messages': [
                'command-message (visible)',
                'skill-instructions (isMeta=true)'
            ],
            'context': 'modified by skill',
            'transitions': ['SKILL_EXECUTION']
        },
        
        'SKILL_EXECUTION': {
            'messages': ['tool_use: bash/python/file'],
            'context': 'skill-scoped permissions',
            'transitions': ['SKILL_EXECUTION', 'RESPONSE_GENERATION']
        },
        
        'RESPONSE_GENERATION': {
            'messages': ['assistant response'],
            'context': 'skill context active',
            'transitions': ['INITIAL', 'SKILL_EXECUTION']
        }
    }
```

---

## 2. Project Structure
```
skill-meta-tool-framework/
├── README.md
├── ARCHITECTURE.md
├── pyproject.toml
├── setup.py
├── requirements.txt
├── requirements-dev.txt
│
├── src/
│   └── skill_framework/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── skill_meta_tool.py      # Core meta-tool implementation
│       │   ├── skill_loader.py          # SKILL.md parser & loader
│       │   ├── message_injector.py      # Two-message pattern
│       │   ├── context_manager.py       # Execution context modification
│       │   └── permission_manager.py    # Tool permission scoping
│       │
│       ├── integration/
│       │   ├── __init__.py
│       │   ├── bedrock_adapter.py       # AWS Bedrock integration
│       │   ├── vertex_adapter.py        # GCP Vertex AI integration
│       │   ├── anthropic_adapter.py     # Direct Anthropic API
│       │   └── base_adapter.py          # Abstract base
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── bash_tool.py             # Bash execution
│       │   ├── file_tool.py             # File operations
│       │   ├── python_tool.py           # Python code execution
│       │   └── tool_registry.py         # Tool management
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── agent_builder.py         # Agent construction
│       │   ├── conversation.py          # Conversation management
│       │   └── session.py               # Session state
│       │
│       └── utils/
│           ├── __init__.py
│           ├── yaml_parser.py
│           ├── code_extractor.py
│           └── logging.py
│
├── skills/
│   ├── README.md
│   ├── _template/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── scripts/
│   │
│   ├── fraud-analysis/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── examples/
│   │   │   └── sample_analysis.py
│   │   └── schemas/
│   │       └── transaction_schema.json
│   │
│   ├── report-generation/
│   │   ├── SKILL.md
│   │   ├── templates/
│   │   │   ├── executive_summary.xlsx
│   │   │   └── compliance_report.pdf
│   │   └── scripts/
│   │       └── format_helper.py
│   │
│   └── data-validation/
│       ├── SKILL.md
│       └── validators/
│           └── schema_validator.py
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_skill_meta_tool.py
│   │   ├── test_skill_loader.py
│   │   ├── test_message_injector.py
│   │   ├── test_context_manager.py
│   │   └── test_permission_manager.py
│   │
│   ├── integration/
│   │   ├── test_bedrock_integration.py
│   │   ├── test_vertex_integration.py
│   │   └── test_end_to_end.py
│   │
│   ├── skills/
│   │   ├── test_fraud_analysis_skill.py
│   │   ├── test_report_generation_skill.py
│   │   └── test_data_validation_skill.py
│   │
│   └── fixtures/
│       ├── sample_skills/
│       ├── sample_data/
│       └── mock_responses/
│
├── examples/
│   ├── basic_usage.py
│   ├── custom_skill.py
│   ├── bedrock_deployment.py
│   ├── vertex_deployment.py
│   └── local_development.py
│
├── docs/
│   ├── getting_started.md
│   ├── skill_creation_guide.md
│   ├── deployment_guide.md
│   ├── api_reference.md
│   └── architecture_deep_dive.md
│
├── deployment/
│   ├── aws/
│   │   ├── agentcore/
│   │   │   ├── Dockerfile
│   │   │   ├── cloudformation.yaml
│   │   │   └── deploy.sh
│   │   └── lambda/
│   │       └── ...
│   │
│   ├── gcp/
│   │   ├── agent_engine/
│   │   │   ├── Dockerfile
│   │   │   └── deploy.py
│   │   └── cloud_run/
│   │       └── ...
│   │
│   └── docker-compose.yml
│
└── scripts/
    ├── create_skill.py
    ├── validate_skills.py
    ├── benchmark.py
    └── migrate_to_skills.py

3. Core Components
3.1 Skill Meta-Tool Core
python# src/skill_framework/core/skill_meta_tool.py

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .skill_loader import SkillLoader
from .message_injector import MessageInjector
from .context_manager import ContextManager
from .permission_manager import PermissionManager


class SkillActivationMode(Enum):
    """Modes for skill activation"""
    AUTO = "auto"           # LLM decides when to activate
    MANUAL = "manual"       # Explicit activation required
    PRELOAD = "preload"     # Load at conversation start


@dataclass
class SkillMetadata:
    """Skill metadata from YAML frontmatter"""
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = None
    activation_mode: SkillActivationMode = SkillActivationMode.AUTO
    
    # Tool requirements
    required_tools: List[str] = None
    optional_tools: List[str] = None
    
    # Execution constraints
    max_execution_time: Optional[int] = None  # seconds
    max_memory: Optional[int] = None  # MB
    network_access: bool = False
    
    # Dependencies
    python_packages: List[str] = None
    system_packages: List[str] = None


@dataclass
class SkillActivationResult:
    """Result of skill activation"""
    success: bool
    skill_name: str
    
    # Messages to inject
    metadata_message: Dict[str, Any]
    instruction_message: Dict[str, Any]
    
    # Context modifications
    modified_context: Dict[str, Any]
    
    # Error info (if failed)
    error: Optional[str] = None
    error_details: Optional[Dict] = None


class SkillMetaTool:
    """
    Meta-tool that manages skill lifecycle following Claude Code architecture.
    
    Key Responsibilities:
    1. Load skill metadata (progressive disclosure)
    2. Implement two-message injection pattern
    3. Modify execution context per skill
    4. Manage tool permissions
    5. Coordinate with LLM for skill selection
    
    Architecture Pattern:
    - Meta-tool appears as single "Skill" tool in tools array
    - LLM decides when to invoke based on task requirements
    - On invocation, loads full skill content on-demand
    - Injects two messages: visible + hidden (isMeta=true)
    - Modifies available tools and permissions
    """
    
    def __init__(
        self,
        skills_directory: Path,
        cache_enabled: bool = True,
        strict_mode: bool = True
    ):
        """
        Initialize Skill Meta-Tool.
        
        Args:
            skills_directory: Path to skills folder
            cache_enabled: Cache loaded skills in memory
            strict_mode: Enforce strict validation
        """
        self.skills_dir = Path(skills_directory)
        self.cache_enabled = cache_enabled
        self.strict_mode = strict_mode
        
        # Core components
        self.loader = SkillLoader(
            skills_dir=self.skills_dir,
            cache_enabled=cache_enabled
        )
        self.message_injector = MessageInjector()
        self.context_manager = ContextManager()
        self.permission_manager = PermissionManager()
        
        # Load metadata only (not full content)
        self.skills_metadata = self.loader.load_all_metadata()
        
        # Active skills in current session
        self.active_skills: Dict[str, Any] = {}
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get tool definition for LLM tools array.
        
        Returns:
            Tool definition dict for "Skill" meta-tool
        """
        return {
            "name": "Skill",
            "description": self._build_tool_description(),
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of skill to activate",
                        "enum": list(self.skills_metadata.keys())
                    }
                },
                "required": ["skill_name"]
            }
        }
    
    def _build_tool_description(self) -> str:
        """
        Build tool description that helps LLM understand when to use skills.
        
        Critical: This is how LLM decides to invoke the Skill meta-tool.
        Must be clear and comprehensive.
        """
        base_desc = (
            "Activate a specialized skill for domain-specific tasks. "
            "Skills provide expert instructions and capabilities for specific domains.\n\n"
            "Available skills:\n"
        )
        
        for name, metadata in self.skills_metadata.items():
            base_desc += f"- {name}: {metadata.description}\n"
        
        base_desc += (
            "\nCall this tool when you need specialized domain expertise. "
            "The skill will load relevant instructions and enable appropriate tools."
        )
        
        return base_desc
    
    def get_system_prompt_section(self) -> str:
        """
        Generate skills section for system prompt.
        
        CRITICAL: Only includes metadata, NOT full instructions.
        This is progressive disclosure - full content loaded on-demand.
        
        Returns:
            String to include in system prompt
        """
        if not self.skills_metadata:
            return ""
        
        section = "\n## Available Skills\n\n"
        section += "You have access to specialized skills for domain-specific tasks:\n\n"
        
        for name, metadata in self.skills_metadata.items():
            section += f"**{name}** (v{metadata.version})\n"
            section += f"  {metadata.description}\n"
            
            if metadata.tags:
                section += f"  Tags: {', '.join(metadata.tags)}\n"
            
            section += "\n"
        
        section += (
            "To activate a skill, use the Skill tool with the skill name. "
            "Once activated, you'll receive detailed instructions for that domain.\n"
        )
        
        return section
    
    async def activate_skill(
        self,
        skill_name: str,
        current_context: Dict[str, Any]
    ) -> SkillActivationResult:
        """
        Activate a skill using two-message pattern.
        
        This is the CORE implementation of the Skills architecture:
        1. Validate skill exists and can be loaded
        2. Load full SKILL.md content (progressive disclosure)
        3. Create metadata message (visible to user)
        4. Create instruction message (hidden, isMeta=true)
        5. Modify execution context (permissions, tools)
        6. Return activation result
        
        Args:
            skill_name: Name of skill to activate
            current_context: Current execution context
            
        Returns:
            SkillActivationResult with messages and context
        """
        
        # Step 1: Validate skill exists
        if skill_name not in self.skills_metadata:
            return SkillActivationResult(
                success=False,
                skill_name=skill_name,
                metadata_message={},
                instruction_message={},
                modified_context=current_context,
                error=f"Skill '{skill_name}' not found",
                error_details={
                    "available_skills": list(self.skills_metadata.keys())
                }
            )
        
        try:
            # Step 2: Load full skill content (progressive disclosure)
            skill_content = self.loader.load_skill(skill_name)
            
            # Step 3: Create metadata message (visible)
            metadata_msg = self.message_injector.create_metadata_message(
                skill_name=skill_name,
                metadata=self.skills_metadata[skill_name]
            )
            
            # Step 4: Create instruction message (hidden, isMeta=true)
            instruction_msg = self.message_injector.create_instruction_message(
                skill_name=skill_name,
                instructions=skill_content.instructions,
                metadata=self.skills_metadata[skill_name]
            )
            
            # Step 5: Modify execution context
            modified_context = self.context_manager.modify_for_skill(
                skill_name=skill_name,
                skill_metadata=self.skills_metadata[skill_name],
                current_context=current_context
            )
            
            # Step 6: Update tool permissions
            modified_context = self.permission_manager.apply_permissions(
                skill_name=skill_name,
                skill_metadata=self.skills_metadata[skill_name],
                context=modified_context
            )
            
            # Track active skill
            self.active_skills[skill_name] = {
                'metadata': self.skills_metadata[skill_name],
                'content': skill_content,
                'activated_at': self._get_timestamp()
            }
            
            return SkillActivationResult(
                success=True,
                skill_name=skill_name,
                metadata_message=metadata_msg,
                instruction_message=instruction_msg,
                modified_context=modified_context
            )
            
        except Exception as e:
            return SkillActivationResult(
                success=False,
                skill_name=skill_name,
                metadata_message={},
                instruction_message={},
                modified_context=current_context,
                error=str(e),
                error_details={"exception_type": type(e).__name__}
            )
    
    def deactivate_skill(self, skill_name: str):
        """Deactivate a skill and restore default context"""
        if skill_name in self.active_skills:
            del self.active_skills[skill_name]
    
    def get_active_skills(self) -> List[str]:
        """Get list of currently active skills"""
        return list(self.active_skills.keys())
    
    def is_skill_active(self, skill_name: str) -> bool:
        """Check if skill is currently active"""
        return skill_name in self.active_skills
    
    def reload_skills(self):
        """Reload all skill metadata (for development)"""
        self.skills_metadata = self.loader.load_all_metadata()
        self.loader.clear_cache()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
3.2 Skill Loader
python# src/skill_framework/core/skill_loader.py

from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass
import yaml


@dataclass
class SkillContent:
    """Full skill content loaded on-demand"""
    name: str
    metadata: 'SkillMetadata'
    instructions: str
    raw_content: str
    file_path: Path
    
    # Supporting files
    scripts: Dict[str, Path] = None
    templates: Dict[str, Path] = None
    examples: Dict[str, Path] = None


class SkillLoader:
    """
    Loads and parses SKILL.md files.
    
    Implements progressive disclosure:
    - Load metadata immediately (frontmatter only)
    - Load full content on-demand when skill activated
    - Cache loaded skills if enabled
    """
    
    def __init__(self, skills_dir: Path, cache_enabled: bool = True):
        self.skills_dir = Path(skills_dir)
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, SkillContent] = {}
    
    def load_all_metadata(self) -> Dict[str, 'SkillMetadata']:
        """
        Load metadata from all SKILL.md files.
        
        Only parses YAML frontmatter, not full content.
        This enables fast startup with minimal memory usage.
        """
        metadata_dict = {}
        
        for skill_path in self.skills_dir.rglob("SKILL.md"):
            try:
                metadata = self._parse_metadata(skill_path)
                if metadata:
                    metadata_dict[metadata.name] = metadata
            except Exception as e:
                print(f"Warning: Failed to load {skill_path}: {e}")
        
        return metadata_dict
    
    def load_skill(self, skill_name: str) -> SkillContent:
        """
        Load full skill content on-demand.
        
        This is called by SkillMetaTool when skill is activated.
        Implements progressive disclosure pattern.
        """
        # Check cache first
        if self.cache_enabled and skill_name in self._cache:
            return self._cache[skill_name]
        
        # Find SKILL.md file
        skill_path = self._find_skill_file(skill_name)
        if not skill_path:
            raise FileNotFoundError(f"SKILL.md not found for '{skill_name}'")
        
        # Load full content
        with open(skill_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # Parse frontmatter and instructions
        metadata, instructions = self._parse_skill_md(raw_content)
        
        # Load supporting files
        skill_dir = skill_path.parent
        scripts = self._find_scripts(skill_dir)
        templates = self._find_templates(skill_dir)
        examples = self._find_examples(skill_dir)
        
        # Create SkillContent object
        skill_content = SkillContent(
            name=skill_name,
            metadata=metadata,
            instructions=instructions,
            raw_content=raw_content,
            file_path=skill_path,
            scripts=scripts,
            templates=templates,
            examples=examples
        )
        
        # Cache if enabled
        if self.cache_enabled:
            self._cache[skill_name] = skill_content
        
        return skill_content
    
    def _parse_metadata(self, skill_path: Path) -> Optional['SkillMetadata']:
        """Parse only YAML frontmatter (metadata)"""
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.startswith('---'):
            return None
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None
        
        frontmatter = yaml.safe_load(parts[1])
        
        from .skill_meta_tool import SkillMetadata, SkillActivationMode
        return SkillMetadata(
            name=frontmatter.get('name'),
            description=frontmatter.get('description', ''),
            version=frontmatter.get('version', '1.0.0'),
            author=frontmatter.get('author'),
            tags=frontmatter.get('tags', []),
            activation_mode=SkillActivationMode(
                frontmatter.get('activation_mode', 'auto')
            ),
            required_tools=frontmatter.get('required_tools', []),
            optional_tools=frontmatter.get('optional_tools', []),
            max_execution_time=frontmatter.get('max_execution_time'),
            max_memory=frontmatter.get('max_memory'),
            network_access=frontmatter.get('network_access', False),
            python_packages=frontmatter.get('python_packages', []),
            system_packages=frontmatter.get('system_packages', [])
        )
    
    def _parse_skill_md(self, content: str) -> Tuple['SkillMetadata', str]:
        """Parse full SKILL.md: metadata + instructions"""
        if not content.startswith('---'):
            raise ValueError("SKILL.md must start with YAML frontmatter")
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError("Invalid SKILL.md format")
        
        metadata = self._parse_metadata_from_yaml(parts[1])
        instructions = parts[2].strip()
        
        return metadata, instructions
    
    def _parse_metadata_from_yaml(self, yaml_str: str) -> 'SkillMetadata':
        """Convert YAML string to SkillMetadata"""
        frontmatter = yaml.safe_load(yaml_str)
        
        from .skill_meta_tool import SkillMetadata, SkillActivationMode
        return SkillMetadata(
            name=frontmatter['name'],
            description=frontmatter.get('description', ''),
            version=frontmatter.get('version', '1.0.0'),
            author=frontmatter.get('author'),
            tags=frontmatter.get('tags', []),
            activation_mode=SkillActivationMode(
                frontmatter.get('activation_mode', 'auto')
            ),
            required_tools=frontmatter.get('required_tools', []),
            optional_tools=frontmatter.get('optional_tools', []),
            max_execution_time=frontmatter.get('max_execution_time'),
            max_memory=frontmatter.get('max_memory'),
            network_access=frontmatter.get('network_access', False),
            python_packages=frontmatter.get('python_packages', []),
            system_packages=frontmatter.get('system_packages', [])
        )
    
    def _find_skill_file(self, skill_name: str) -> Optional[Path]:
        """Find SKILL.md file for given skill name"""
        # Try direct match: skills/skill-name/SKILL.md
        direct_path = self.skills_dir / skill_name / "SKILL.md"
        if direct_path.exists():
            return direct_path
        
        # Try searching all SKILL.md files
        for skill_path in self.skills_dir.rglob("SKILL.md"):
            metadata = self._parse_metadata(skill_path)
            if metadata and metadata.name == skill_name:
                return skill_path
        
        return None
    
    def _find_scripts(self, skill_dir: Path) -> Dict[str, Path]:
        """Find script files in skill directory"""
        scripts = {}
        scripts_dir = skill_dir / "scripts"
        
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.py"):
                scripts[script.stem] = script
        
        return scripts
    
    def _find_templates(self, skill_dir: Path) -> Dict[str, Path]:
        """Find template files"""
        templates = {}
        templates_dir = skill_dir / "templates"
        
        if templates_dir.exists():
            for template in templates_dir.iterdir():
                if template.is_file():
                    templates[template.name] = template
        
        return templates
    
    def _find_examples(self, skill_dir: Path) -> Dict[str, Path]:
        """Find example files"""
        examples = {}
        examples_dir = skill_dir / "examples"
        
        if examples_dir.exists():
            for example in examples_dir.glob("*.py"):
                examples[example.stem] = example
        
        return examples
    
    def clear_cache(self):
        """Clear skill content cache"""
        self._cache.clear()
3.3 Message Injector
python# src/skill_framework/core/message_injector.py

from typing import Dict, Any
from datetime import datetime


class MessageInjector:
    """
    Implements two-message injection pattern for skills.
    
    Message 1: Visible metadata (command-message)
    - Shows in UI/logs
    - Indicates skill activation
    - Helps user understand what's happening
    
    Message 2: Hidden instructions (isMeta=true)
    - Not shown in UI
    - Contains full SKILL.md instructions
    - Provides context to LLM
    """
    
    def create_metadata_message(
        self,
        skill_name: str,
        metadata: 'SkillMetadata'
    ) -> Dict[str, Any]:
        """
        Create visible metadata message (Message 1).
        
        This message appears in conversation history and UI.
        Uses <command-message> XML tag for identification.
        """
        return {
            'role': 'user',
            'content': (
                f'<command-message>'
                f'Activating skill: {skill_name} (v{metadata.version})'
                f'</command-message>'
            ),
            'metadata': {
                'type': 'skill_activation',
                'skill_name': skill_name,
                'skill_version': metadata.version,
                'timestamp': self._get_timestamp(),
                'visible': True
            }
        }
    
    def create_instruction_message(
        self,
        skill_name: str,
        instructions: str,
        metadata: 'SkillMetadata'
    ) -> Dict[str, Any]:
        """
        Create hidden instruction message (Message 2).
        
        CRITICAL: This message has isMeta=true which means:
        - It's sent to the LLM for context
        - It's NOT shown in UI/conversation history
        - It provides the actual skill instructions
        
        This is the core of progressive disclosure.
        """
        return {
            'role': 'user',
            'content': self._format_instructions(
                skill_name,
                instructions,
                metadata
            ),
            'isMeta': True,  # ← CRITICAL: Hides from UI
            'metadata': {
                'type': 'skill_instructions',
                'skill_name': skill_name,
                'skill_version': metadata.version,
                'timestamp': self._get_timestamp(),
                'visible': False
            }
        }
    
    def _format_instructions(
        self,
        skill_name: str,
        instructions: str,
        metadata: 'SkillMetadata'
    ) -> str:
        """
        Format skill instructions for injection.
        
        Adds skill context and metadata to instructions.
        """
        formatted = f"# {skill_name} Skill\n\n"
        
        # Add metadata context
        formatted += f"**Version:** {metadata.version}\n"
        
        if metadata.tags:
            formatted += f"**Tags:** {', '.join(metadata.tags)}\n"
        
        if metadata.required_tools:
            formatted += f"**Required Tools:** {', '.join(metadata.required_tools)}\n"
        
        formatted += "\n---\n\n"
        
        # Add actual instructions
        formatted += instructions
        
        # Add constraints if any
        if metadata.max_execution_time:
            formatted += f"\n\n**Execution Time Limit:** {metadata.max_execution_time}s"
        
        if not metadata.network_access:
            formatted += "\n\n**Note:** Network access is disabled for this skill."
        
        return formatted
    
    def _get_timestamp(self) -> str:
        """Get ISO format timestamp"""
        return datetime.utcnow().isoformat() + 'Z'
3.4 Context Manager
python# src/skill_framework/core/context_manager.py

from typing import Dict, Any
from copy import deepcopy


class ContextManager:
    """
    Manages execution context modifications for skills.
    
    Each skill can modify the execution context to enable/disable
    specific capabilities, tools, or permissions.
    """
    
    def __init__(self):
        self.default_context = {
            'allowed_tools': [],
            'file_permissions': 'none',
            'network_access': False,
            'max_execution_time': 300,  # 5 minutes
            'max_memory': 2048,  # 2GB
            'working_directory': '/tmp',
            'environment_variables': {}
        }
    
    def modify_for_skill(
        self,
        skill_name: str,
        skill_metadata: 'SkillMetadata',
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Modify execution context based on skill requirements.
        
        This is where tool permissions are scoped per skill.
        """
        # Start with current context
        modified = deepcopy(current_context)
        
        # Apply skill-specific tool permissions
        if skill_metadata.required_tools:
            modified['allowed_tools'] = list(set(
                modified.get('allowed_tools', []) + 
                skill_metadata.required_tools
            ))
        
        # Add optional tools if available
        if skill_metadata.optional_tools:
            available_tools = modified.get('all_available_tools', [])
            for tool in skill_metadata.optional_tools:
                if tool in available_tools and tool not in modified['allowed_tools']:
                    modified['allowed_tools'].append(tool)
        
        # Apply execution constraints
        if skill_metadata.max_execution_time:
            modified['max_execution_time'] = min(
                modified.get('max_execution_time', 999999),
                skill_metadata.max_execution_time
            )
        
        if skill_metadata.max_memory:
            modified['max_memory'] = min(
                modified.get('max_memory', 999999),
                skill_metadata.max_memory
            )
        
        # Network access
        if skill_metadata.network_access:
            modified['network_access'] = True
        
        # Skill-specific context modifications
        modified = self._apply_skill_specific_context(
            skill_name,
            skill_metadata,
            modified
        )
        
        # Track active skill
        modified['active_skill'] = skill_name
        modified['skill_version'] = skill_metadata.version
        
        return modified
    
    def _apply_skill_specific_context(
        self,
        skill_name: str,
        skill_metadata: 'SkillMetadata',
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply skill-specific context modifications.
        
        This is where you define custom behavior per skill.
        """
        
        # Example: PDF processing needs file operations
        if skill_name == 'pdf' or 'pdf' in skill_metadata.tags:
            context['file_permissions'] = 'read_write'
            context['allowed_file_extensions'] = ['.pdf', '.txt', '.json']
        
        # Example: Data analysis needs more memory
        if 'data-analysis' in skill_metadata.tags:
            context['max_memory'] = max(context.get('max_memory', 2048), 4096)
        
        # Example: Report generation needs output directory
        if skill_name == 'report-generation':
            context['output_directory'] = '/tmp/reports'
            context['file_permissions'] = 'read_write'
        
        # Example: Fraud detection needs database access
        if skill_name == 'fraud-analysis':
            context['database_access'] = True
            context['allowed_tables'] = ['transactions', 'users', 'alerts']
        
        return context
    
    def restore_default_context(self) -> Dict[str, Any]:
        """Restore default execution context"""
        return deepcopy(self.default_context)
3.5 Permission Manager
python# src/skill_framework/core/permission_manager.py

from typing import Dict, Any, List, Set
from enum import Enum


class PermissionLevel(Enum):
    """Permission levels for tools"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class PermissionManager:
    """
    Manages fine-grained tool permissions for skills.
    
    Different skills need different tool access:
    - PDF skill needs file read/write
    - Fraud analysis needs database query
    - Report generation needs file write only
    """
    
    def __init__(self):
        # Tool permission matrix
        self.tool_permissions = {
            'bash_tool': PermissionLevel.EXECUTE,
            'file_read': PermissionLevel.READ,
            'file_write': PermissionLevel.WRITE,
            'python_execute': PermissionLevel.EXECUTE,
            'database_query': PermissionLevel.READ,
            'database_write': PermissionLevel.WRITE,
            'network_request': PermissionLevel.EXECUTE,
        }
        
        # Skill-specific permission profiles
        self.skill_profiles = {
            'pdf': {
                'bash_tool': PermissionLevel.EXECUTE,
                'file_read': PermissionLevel.READ,
                'file_write': PermissionLevel.WRITE,
                'python_execute': PermissionLevel.EXECUTE,
            },
            'fraud-analysis': {
                'bash_tool': PermissionLevel.EXECUTE,
                'python_execute': PermissionLevel.EXECUTE,
                'database_query': PermissionLevel.READ,
                'file_read': PermissionLevel.READ,
            },
            'report-generation': {
                'bash_tool': PermissionLevel.EXECUTE,
                'python_execute': PermissionLevel.EXECUTE,
                'file_read': PermissionLevel.READ,
                'file_write': PermissionLevel.WRITE,
            },
            'data-validation': {
                'bash_tool': PermissionLevel.EXECUTE,
                'python_execute': PermissionLevel.EXECUTE,
                'file_read': PermissionLevel.READ,
            }
        }
    
    def apply_permissions(
        self,
        skill_name: str,
        skill_metadata: 'SkillMetadata',
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply tool permissions for skill.
        
        Returns modified context with permission constraints.
        """
        # Get skill profile or use metadata
        if skill_name in self.skill_profiles:
            permissions = self.skill_profiles[skill_name]
        else:
            permissions = self._build_permissions_from_metadata(skill_metadata)
        
        # Apply to context
        context['tool_permissions'] = permissions
        context['allowed_tools'] = list(permissions.keys())
        
        return context
    
    def _build_permissions_from_metadata(
        self,
        metadata: 'SkillMetadata'
    ) -> Dict[str, PermissionLevel]:
        """Build permission dict from skill metadata"""
        permissions = {}
        
        for tool in metadata.required_tools:
            # Default to EXECUTE for required tools
            permissions[tool] = PermissionLevel.EXECUTE
        
        for tool in (metadata.optional_tools or []):
            # Optional tools get limited permissions
            permissions[tool] = PermissionLevel.READ
        
        return permissions
    
    def check_permission(
        self,
        tool_name: str,
        required_level: PermissionLevel,
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if tool can be used with required permission level.
        
        Args:
            tool_name: Name of tool to check
            required_level: Minimum required permission
            context: Current execution context
            
        Returns:
            True if permission granted, False otherwise
        """
        permissions = context.get('tool_permissions', {})
        
        if tool_name not in permissions:
            return False
        
        granted_level = permissions[tool_name]
        
        # Permission hierarchy
        hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.EXECUTE: 3,
            PermissionLevel.ADMIN: 4
        }
        
        return hierarchy[granted_level] >= hierarchy[required_level]

4. Implementation Skeleton
4.1 Agent Builder
python# src/skill_framework/agent/agent_builder.py

from typing import List, Dict, Any, Optional
from pathlib import Path

from ..core.skill_meta_tool import SkillMetaTool
from ..tools.tool_registry import ToolRegistry
from ..integration.base_adapter import BaseLLMAdapter


class AgentBuilder:
    """
    Builds agents with Skills support.
    
    Orchestrates:
    - Skill meta-tool setup
    - Tool registry
    - LLM adapter integration
    - System prompt construction
    """
    
    def __init__(
        self,
        skills_directory: Path,
        llm_adapter: BaseLLMAdapter,
        enable_cache: bool = True
    ):
        """
        Initialize agent builder.
        
        Args:
            skills_directory: Path to skills folder
            llm_adapter: LLM integration adapter (Bedrock/Vertex/etc)
            enable_cache: Enable skill caching
        """
        self.skills_dir = Path(skills_directory)
        self.llm_adapter = llm_adapter
        
        # Initialize skill meta-tool
        self.skill_meta_tool = SkillMetaTool(
            skills_directory=self.skills_dir,
            cache_enabled=enable_cache
        )
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        
        # Register Skill meta-tool
        self.tool_registry.register_tool(
            name="Skill",
            definition=self.skill_meta_tool.get_tool_definition(),
            handler=self._handle_skill_activation
        )
    
    def build_agent(
        self,
        name: str,
        base_instruction: str,
        additional_tools: Optional[List[Dict]] = None
    ) -> 'Agent':
        """
        Build complete agent with Skills support.
        
        Args:
            name: Agent name
            base_instruction: Base system instruction
            additional_tools: Extra tools to register
            
        Returns:
            Configured Agent instance
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(base_instruction)
        
        # Collect all tools
        tools = self._collect_tools(additional_tools)
        
        # Create agent instance
        from .agent import Agent
        agent = Agent(
            name=name,
            system_prompt=system_prompt,
            tools=tools,
            llm_adapter=self.llm_adapter,
            skill_meta_tool=self.skill_meta_tool,
            tool_registry=self.tool_registry
        )
        
        return agent
    
    def _build_system_prompt(self, base_instruction: str) -> str:
        """Build complete system prompt including skills section"""
        prompt = base_instruction
        
        # Add skills section (metadata only)
        skills_section = self.skill_meta_tool.get_system_prompt_section()
        if skills_section:
            prompt += "\n\n" + skills_section
        
        # Add tool usage guidelines
        prompt += "\n\n## Tool Usage\n\n"
        prompt += (
            "You have access to various tools. To use a skill, call the Skill tool "
            "with the appropriate skill name. Once a skill is activated, follow its "
            "specific instructions carefully.\n"
        )
        
        return prompt
    
    def _collect_tools(
        self,
        additional_tools: Optional[List[Dict]]
    ) -> List[Dict[str, Any]]:
        """Collect all tool definitions"""
        tools = []
        
        # Add Skill meta-tool (always first)
        tools.append(self.skill_meta_tool.get_tool_definition())
        
        # Add registered tools
        tools.extend(self.tool_registry.get_all_tool_definitions())
        
        # Add additional tools if provided
        if additional_tools:
            tools.extend(additional_tools)
        
        return tools
    
    async def _handle_skill_activation(
        self,
        skill_name: str,
        context: Dict[str, Any]
    ):
        """Handle Skill tool invocation"""
        result = await self.skill_meta_tool.activate_skill(
            skill_name=skill_name,
            current_context=context
        )
        
        return result
4.2 Conversation Manager
python# src/skill_framework/agent/conversation.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Single conversation message"""
    role: str  # 'user' or 'assistant'
    content: Any
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    isMeta: bool = False  # Hidden message flag


@dataclass
class ConversationState:
    """State of ongoing conversation"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    active_skills: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConversationManager:
    """
    Manages conversation state and message history.
    
    Handles:
    - Message injection (two-message pattern)
    - Context tracking
    - Skill activation state
    - History management
    """
    
    def __init__(self):
        self.conversations: Dict[str, ConversationState] = {}
    
    def create_conversation(self, session_id: str) -> ConversationState:
        """Create new conversation"""
        state = ConversationState(session_id=session_id)
        self.conversations[session_id] = state
        return state
    
    def get_conversation(self, session_id: str) -> Optional[ConversationState]:
        """Get existing conversation"""
        return self.conversations.get(session_id)
    
    def add_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Add user message to conversation"""
        state = self.get_conversation(session_id)
        if not state:
            state = self.create_conversation(session_id)
        
        message = Message(
            role='user',
            content=content,
            metadata=metadata or {}
        )
        
        state.messages.append(message)
        state.updated_at = datetime.utcnow().isoformat()
    
    def add_assistant_message(
        self,
        session_id: str,
        content: Any,
        metadata: Optional[Dict] = None
    ):
        """Add assistant response"""
        state = self.get_conversation(session_id)
        if not state:
            raise ValueError(f"Conversation {session_id} not found")
        
        message = Message(
            role='assistant',
            content=content,
            metadata=metadata or {}
        )
        
        state.messages.append(message)
        state.updated_at = datetime.utcnow().isoformat()
    
    def inject_skill_messages(
        self,
        session_id: str,
        metadata_message: Dict[str, Any],
        instruction_message: Dict[str, Any]
    ):
        """
        Inject two-message pattern for skill activation.
        
        Message 1: Visible metadata
        Message 2: Hidden instructions (isMeta=true)
        """
        state = self.get_conversation(session_id)
        if not state:
            raise ValueError(f"Conversation {session_id} not found")
        
        # Add metadata message (visible)
        msg1 = Message(
            role=metadata_message['role'],
            content=metadata_message['content'],
            metadata=metadata_message.get('metadata', {}),
            isMeta=False
        )
        state.messages.append(msg1)
        
        # Add instruction message (hidden)
        msg2 = Message(
            role=instruction_message['role'],
            content=instruction_message['content'],
            metadata=instruction_message.get('metadata', {}),
            isMeta=True  # Hidden from UI
        )
        state.messages.append(msg2)
        
        state.updated_at = datetime.utcnow().isoformat()
    
    def get_messages_for_api(
        self,
        session_id: str,
        include_meta: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get messages formatted for LLM API.
        
        Args:
            session_id: Conversation ID
            include_meta: Include hidden (isMeta=true) messages
            
        Returns:
            List of message dicts for API
        """
        state = self.get_conversation(session_id)
        if not state:
            return []
        
        api_messages = []
        
        for msg in state.messages:
            # Skip meta messages if not including them
            if msg.isMeta and not include_meta:
                continue
            
            api_messages.append({
                'role': msg.role,
                'content': msg.content,
                # Don't include isMeta in API call,
                # it's just for internal tracking
            })
        
        return api_messages
    
    def get_visible_messages(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get only visible messages (for UI display)"""
        state = self.get_conversation(session_id)
        if not state:
            return []
        
        return [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'metadata': msg.metadata
            }
            for msg in state.messages
            if not msg.isMeta  # Exclude hidden messages
        ]
    
    def update_context(
        self,
        session_id: str,
        context_updates: Dict[str, Any]
    ):
        """Update conversation context"""
        state = self.get_conversation(session_id)
        if state:
            state.context.update(context_updates)
            state.updated_at = datetime.utcnow().isoformat()
    
    def activate_skill(
        self,
        session_id: str,
        skill_name: str
    ):
        """Mark skill as active in conversation"""
        state = self.get_conversation(session_id)
        if state and skill_name not in state.active_skills:
            state.active_skills.append(skill_name)
    
    def deactivate_skill(
        self,
        session_id: str,
        skill_name: str
    ):
        """Mark skill as inactive"""
        state = self.get_conversation(session_id)
        if state and skill_name in state.active_skills:
            state.active_skills.remove(skill_name)

5. Testing Framework
5.1 Test Structure
python# tests/unit/test_skill_meta_tool.py

import pytest
from pathlib import Path
from skill_framework.core.skill_meta_tool import (
    SkillMetaTool,
    SkillMetadata,
    SkillActivationMode
)


class TestSkillMetaTool:
    """Test suite for SkillMetaTool"""
    
    @pytest.fixture
    def skills_dir(self, tmp_path):
        """Create temporary skills directory"""
        skills = tmp_path / "skills"
        skills.mkdir()
        
        # Create test skill
        test_skill = skills / "test-skill"
        test_skill.mkdir()
        
        skill_md = test_skill / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: A test skill
version: 1.0.0
required_tools: ["bash_tool", "python_execute"]
---

# Test Skill Instructions

This is a test skill for unit testing.

## Usage

1. Step one
2. Step two
""")
        
        return skills
    
    @pytest.fixture
    def skill_meta_tool(self, skills_dir):
        """Create SkillMetaTool instance"""
        return SkillMetaTool(
            skills_directory=skills_dir,
            cache_enabled=True
        )
    
    def test_loads_skill_metadata(self, skill_meta_tool):
        """Test that metadata is loaded correctly"""
        assert "test-skill" in skill_meta_tool.skills_metadata
        
        metadata = skill_meta_tool.skills_metadata["test-skill"]
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert metadata.version == "1.0.0"
        assert "bash_tool" in metadata.required_tools
    
    def test_get_tool_definition(self, skill_meta_tool):
        """Test tool definition generation"""
        tool_def = skill_meta_tool.get_tool_definition()
        
        assert tool_def["name"] == "Skill"
        assert "description" in tool_def
        assert "input_schema" in tool_def
        assert "test-skill" in tool_def["input_schema"]["properties"]["skill_name"]["enum"]
    
    def test_get_system_prompt_section(self, skill_meta_tool):
        """Test system prompt section generation"""
        section = skill_meta_tool.get_system_prompt_section()
        
        assert "test-skill" in section
        assert "A test skill" in section
        assert "Skill tool" in section
    
    @pytest.mark.asyncio
    async def test_activate_skill_success(self, skill_meta_tool):
        """Test successful skill activation"""
        context = {'allowed_tools': []}
        
        result = await skill_meta_tool.activate_skill(
            skill_name="test-skill",
            current_context=context
        )
        
        assert result.success
        assert result.skill_name == "test-skill"
        assert result.metadata_message['role'] == 'user'
        assert '<command-message>' in result.metadata_message['content']
        assert result.instruction_message['isMeta'] is True
        assert "Test Skill Instructions" in result.instruction_message['content']
    
    @pytest.mark.asyncio
    async def test_activate_nonexistent_skill(self, skill_meta_tool):
        """Test activating skill that doesn't exist"""
        context = {}
        
        result = await skill_meta_tool.activate_skill(
            skill_name="nonexistent",
            current_context=context
        )
        
        assert not result.success
        assert "not found" in result.error
    
    def test_progressive_disclosure(self, skill_meta_tool):
        """Test that metadata is loaded without full content"""
        # Metadata should be loaded
        assert "test-skill" in skill_meta_tool.skills_metadata
        
        # Full content should not be in cache yet
        assert "test-skill" not in skill_meta_tool.loader._cache
    
    @pytest.mark.asyncio
    async def test_two_message_pattern(self, skill_meta_tool):
        """Test two-message injection pattern"""
        context = {}
        
        result = await skill_meta_tool.activate_skill(
            skill_name="test-skill",
            current_context=context
        )
        
        # Message 1: Visible metadata
        msg1 = result.metadata_message
        assert msg1['metadata']['visible'] is True
        assert msg1['metadata']['type'] == 'skill_activation'
        
        # Message 2: Hidden instructions
        msg2 = result.instruction_message
        assert msg2['isMeta'] is True
        assert msg2['metadata']['visible'] is False
        assert msg2['metadata']['type'] == 'skill_instructions'
    
    @pytest.mark.asyncio
    async def test_context_modification(self, skill_meta_tool):
        """Test that context is modified correctly"""
        context = {
            'allowed_tools': [],
            'max_execution_time': 600
        }
        
        result = await skill_meta_tool.activate_skill(
            skill_name="test-skill",
            current_context=context
        )
        
        modified_context = result.modified_context
        
        # Should include required tools
        assert "bash_tool" in modified_context['allowed_tools']
        assert "python_execute" in modified_context['allowed_tools']
        
        # Should track active skill
        assert modified_context['active_skill'] == "test-skill"
5.2 Integration Tests
python# tests/integration/test_end_to_end.py

import pytest
from skill_framework.agent.agent_builder import AgentBuilder
from skill_framework.integration.bedrock_adapter import BedrockAdapter


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_skill_activation(skills_dir, bedrock_credentials):
    """Test complete skill activation flow"""
    
    # Setup
    llm_adapter = BedrockAdapter(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region="us-west-2"
    )
    
    builder = AgentBuilder(
        skills_directory=skills_dir,
        llm_adapter=llm_adapter
    )
    
    agent = builder.build_agent(
        name="test-agent",
        base_instruction="You are a helpful assistant."
    )
    
    # Test query that should trigger skill
    response = await agent.query(
        "Analyze this CSV file for fraud patterns",
        session_id="test-session-1"
    )
    
    # Verify skill was activated
    conversation = agent.conversation_manager.get_conversation("test-session-1")
    assert "fraud-analysis" in conversation.active_skills
    
    # Verify two messages were injected
    messages = conversation.messages
    skill_activation_messages = [
        m for m in messages
        if m.metadata.get('type') in ['skill_activation', 'skill_instructions']
    ]
    assert len(skill_activation_messages) == 2
    
    # Verify one is visible, one is hidden
    visible = [m for m in skill_activation_messages if not m.isMeta]
    hidden = [m for m in skill_activation_messages if m.isMeta]
    
    assert len(visible) == 1
    assert len(hidden) == 1
    
    # Verify context was modified
    assert conversation.context.get('active_skill') == 'fraud-analysis'

6. Deployment Guide
6.1 Local Development
bash# setup_dev.sh

#!/bin/bash
set -e

echo "Setting up Skills Framework development environment..."

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Create skills directory structure
mkdir -p skills/_template
mkdir -p skills/fraud-analysis
mkdir -p skills/report-generation

# Copy template
cp templates/SKILL.template.md skills/_template/SKILL.md

# Run tests
pytest tests/

echo "Development environment ready!"
6.2 AgentCore Deployment
python# deployment/aws/agentcore/deploy.py

"""
Deploy Skills-enabled agent to AWS Bedrock AgentCore.

Usage:
    python deploy.py --name fraud-agent --region us-west-2
"""

import argparse
from pathlib import Path
import boto3
import zipfile
import tempfile


def package_agent(skills_dir: Path, output_path: Path):
    """Package agent and skills for deployment"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add source code
        for py_file in Path('src').rglob('*.py'):
            zf.write(py_file, py_file.relative_to('src'))
        
        # Add skills
        for skill_file in skills_dir.rglob('*'):
            if skill_file.is_file():
                zf.write(skill_file, f"skills/{skill_file.relative_to(skills_dir)}")
        
        # Add requirements
        zf.write('requirements.txt', 'requirements.txt')


def deploy_to_agentcore(
    agent_name: str,
    package_path: Path,
    region: str
):
    """Deploy package to AgentCore"""
    # Upload to S3
    s3 = boto3.client('s3', region_name=region)
    bucket = f"{agent_name}-deployment-{boto3.client('sts').get_caller_identity()['Account']}"
    
    # Create bucket if doesn't exist
    try:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
    except:
        pass
    
    # Upload package
    s3.upload_file(str(package_path), bucket, f"{agent_name}.zip")
    
    # Deploy via AgentCore (pseudo-code - use actual AgentCore CLI/SDK)
    print(f"Deploying {agent_name} to AgentCore...")
    # agentcore.deploy(...)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--region", default="us-west-2")
    
    args = parser.parse_args()
    
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        package_agent(Path('skills'), Path(tmp.name))
        deploy_to_agentcore(args.name, Path(tmp.name), args.region)
