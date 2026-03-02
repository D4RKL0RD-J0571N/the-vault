"""Symbol type definitions and normalization for The Vault parser."""

from enum import Enum
from typing import Dict, Optional


class SymbolType(str, Enum):
    """Standardized symbol types across all languages."""
    
    # Object-oriented types
    CLASS = "class"
    INTERFACE = "interface"
    
    # Function-like types
    METHOD = "method"
    FUNCTION = "function"
    CONSTRUCTOR = "constructor"
    
    # Data types
    FIELD = "field"
    PROPERTY = "property"
    CONSTANT = "constant"
    ENUM = "enum"
    
    # Other types
    VARIABLE = "variable"
    PARAMETER = "parameter"
    NAMESPACE = "namespace"
    MODULE = "module"


class LanguageSpecificMapping:
    """Maps language-specific node types to standardized symbol types."""
    
    # C# mappings
    CSHARP_MAPPING: Dict[str, SymbolType] = {
        "class_declaration": SymbolType.CLASS,
        "interface_declaration": SymbolType.INTERFACE,
        "method_declaration": SymbolType.METHOD,
        "constructor_declaration": SymbolType.CONSTRUCTOR,
        "field_declaration": SymbolType.FIELD,
        "property_declaration": SymbolType.PROPERTY,
        "enum_declaration": SymbolType.ENUM,
        "constant_declaration": SymbolType.CONSTANT,
    }
    
    # Java mappings
    JAVA_MAPPING: Dict[str, SymbolType] = {
        "class_declaration": SymbolType.CLASS,
        "interface_declaration": SymbolType.INTERFACE,
        "method_declaration": SymbolType.METHOD,
        "constructor_declaration": SymbolType.CONSTRUCTOR,
        "field_declaration": SymbolType.FIELD,
        "enum_declaration": SymbolType.ENUM,
        "constant_declaration": SymbolType.CONSTANT,
    }
    
    # Python mappings
    PYTHON_MAPPING: Dict[str, SymbolType] = {
        "class_definition": SymbolType.CLASS,
        "function_definition": SymbolType.FUNCTION,
        "async_function_definition": SymbolType.FUNCTION,
        "assignment": SymbolType.VARIABLE,  # Will be filtered for constants
    }
    
    # JavaScript/TypeScript mappings
    JAVASCRIPT_MAPPING: Dict[str, SymbolType] = {
        "class_declaration": SymbolType.CLASS,
        "function_declaration": SymbolType.FUNCTION,
        "method_definition": SymbolType.METHOD,
        "arrow_function": SymbolType.FUNCTION,
        "variable_declaration": SymbolType.VARIABLE,
        "property_definition": SymbolType.PROPERTY,
    }
    
    # RenPy mappings (custom)
    RENPY_MAPPING: Dict[str, SymbolType] = {
        "label": SymbolType.FUNCTION,  # RenPy labels are like functions
        "character": SymbolType.CLASS,  # RenPy characters are like classes
        "scene": SymbolType.FUNCTION,   # RenPy scenes are like functions
    }


def normalize_symbol_type(node_type: str, language: str) -> Optional[SymbolType]:
    """Normalize language-specific node types to standard symbol types."""
    language = language.lower()
    
    # Get the appropriate mapping for the language
    if language in ["csharp", "c#"]:
        mapping = LanguageSpecificMapping.CSHARP_MAPPING
    elif language == "java":
        mapping = LanguageSpecificMapping.JAVA_MAPPING
    elif language == "python":
        mapping = LanguageSpecificMapping.PYTHON_MAPPING
    elif language in ["javascript", "typescript", "js", "ts"]:
        mapping = LanguageSpecificMapping.JAVASCRIPT_MAPPING
    elif language == "renpy":
        mapping = LanguageSpecificMapping.RENPY_MAPPING
    else:
        return None
    
    return mapping.get(node_type)


def is_constant_symbol(name: str, language: str) -> bool:
    """Determine if a symbol represents a constant based on naming conventions."""
    name_upper = name.upper()
    
    if language in ["python", "javascript", "typescript"]:
        # Constants are typically ALL_CAPS
        return name_upper == name
    elif language in ["java", "csharp"]:
        # Constants are typically static final (handled elsewhere)
        return False
    else:
        return False


def get_method_visibility(modifiers: list[str], language: str) -> str:
    """Extract method visibility from modifiers."""
    if not modifiers:
        return "public"  # Default assumption
    
    modifiers_lower = [m.lower() for m in modifiers]
    
    if language in ["java", "csharp"]:
        if "private" in modifiers_lower:
            return "private"
        elif "protected" in modifiers_lower:
            return "protected"
        elif "public" in modifiers_lower:
            return "public"
        else:
            return "package" if language == "java" else "internal"
    
    elif language in ["javascript", "typescript"]:
        # JavaScript doesn't have explicit visibility modifiers
        return "public"
    
    elif language == "python":
        # Python uses naming conventions
        return "private" if any(m.startswith("_") for m in modifiers) else "public"
    
    else:
        return "public"


def build_qualified_name(parts: list[str], language: str) -> str:
    """Build a qualified name from name parts."""
    if not parts:
        return ""
    
    # Filter out empty parts
    parts = [p for p in parts if p]
    
    if language in ["java", "csharp"]:
        return ".".join(parts)
    elif language in ["javascript", "typescript"]:
        return ".".join(parts)
    elif language == "python":
        return ".".join(parts)
    else:
        return ".".join(parts)


def extract_signature(node_text: str, symbol_type: SymbolType, language: str) -> str:
    """Extract a clean signature from node text."""
    if not node_text:
        return ""
    
    # Remove extra whitespace and normalize
    lines = [line.strip() for line in node_text.split("\n") if line.strip()]
    
    if not lines:
        return ""
    
    # For most types, the first line contains the signature
    if symbol_type in [SymbolType.CLASS, SymbolType.INTERFACE, SymbolType.ENUM]:
        return lines[0]
    
    elif symbol_type in [SymbolType.METHOD, SymbolType.FUNCTION, SymbolType.CONSTRUCTOR]:
        # Find the line with the opening brace or colon
        for line in lines:
            if any(char in line for char in ["{", ":", "->"]):
                return line
        return lines[0]
    
    elif symbol_type in [SymbolType.FIELD, SymbolType.PROPERTY, SymbolType.CONSTANT]:
        return lines[0]
    
    else:
        return lines[0]


def detect_todo_comments(source_code: str) -> bool:
    """Detect if source code contains TODO or FIXME comments."""
    if not source_code:
        return False
    
    # Common TODO patterns across languages
    todo_patterns = [
        "TODO",
        "FIXME", 
        "HACK",
        "XXX",
        "NOTE",
        "BUG",
    ]
    
    source_upper = source_code.upper()
    
    return any(pattern in source_upper for pattern in todo_patterns)
