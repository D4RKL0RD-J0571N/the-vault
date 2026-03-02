"""Language-specific symbol extractors using tree-sitter."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import tree_sitter

try:
    from tree_sitter_languages import get_language, get_parser
except ImportError:
    from tree_sitter_language_pack import get_language, get_parser

from vault.exceptions import ParsingError
from vault.parser.symbol_types import (SymbolType, build_qualified_name,
                                       detect_todo_comments, extract_signature,
                                       get_method_visibility,
                                       is_constant_symbol,
                                       normalize_symbol_type)
from vault.storage.models import Symbol


class SymbolExtractor:
    """Base class for language-specific symbol extractors."""

    def __init__(self, language: str) -> None:
        self.language = language
        self.parser = None
        self.tree_sitter_lang = None
        self._setup_parser()

    def _setup_parser(self) -> None:
        """Set up tree-sitter parser for the language."""
        try:
            self.tree_sitter_lang = get_language(self.language)
            self.parser = get_parser(self.language)
        except Exception as e:
            raise ParsingError(f"Failed to setup parser for {self.language}: {e}")

    def extract_symbols(self, file_path: Path, project_id: str) -> List[Symbol]:
        """Extract symbols from a file."""
        if not self.parser:
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        if not source_code.strip():
            return []

        symbols: list[Symbol] = []

        try:
            tree = self.parser.parse(bytes(source_code, "utf-8"))
            # Extract symbols using language-specific logic
            self._extract_from_node(
                tree.root_node,
                source_code,
                file_path,
                project_id,
                symbols,
            )
            return symbols

        except Exception as e:
            raise ParsingError(f"Failed to parse {file_path}: {e}")

    def _extract_from_node(
        self,
        node: tree_sitter.Node,
        source_code: str,
        file_path: Path,
        project_id: str,
        symbols: List[Symbol],
        parent_name: str = "",
    ) -> None:
        """Recursively extract symbols from tree-sitter nodes."""
        # Override in subclasses
        pass

    def _get_node_text(self, node: tree_sitter.Node, source_code: str) -> str:
        """Get text content of a tree-sitter node."""
        return source_code[node.start_byte : node.end_byte]

    def _has_todo_near_node(self, node: tree_sitter.Node, source_code: str) -> bool:
        """Check if node or its preceding comments have a TODO."""
        # Check node itself
        if detect_todo_comments(self._get_node_text(node, source_code)):
            return True

        # Check preceding sibling comments
        prev = node.prev_sibling
        while prev and "comment" in prev.type:
            if detect_todo_comments(self._get_node_text(prev, source_code)):
                return True
            prev = prev.prev_sibling

        return False

    def _get_symbol_name(
        self, node: tree_sitter.Node, source_code: str
    ) -> Optional[str]:
        """Extract symbol name from a node."""
        # Override in subclasses
        return None

    def _get_line_range(self, node: tree_sitter.Node) -> Tuple[int, int]:
        """Get line range for a node."""
        return (node.start_point[0] + 1, node.end_point[0] + 1)  # 1-based indexing


class CSharpExtractor(SymbolExtractor):
    """C# symbol extractor."""

    def __init__(self) -> None:
        super().__init__("csharp")

    def _extract_from_node(
        self,
        node: tree_sitter.Node,
        source_code: str,
        file_path: Path,
        project_id: str,
        symbols: List[Symbol],
        parent_name: str = "",
    ) -> None:
        """Extract symbols from C# AST."""
        node_type = node.type
        symbol_type = normalize_symbol_type(node_type, "csharp")

        name = None
        qualified_name = parent_name

        if symbol_type:
            name = self._get_symbol_name(node, source_code)
            if name:
                qualified_name = build_qualified_name([parent_name, name], "csharp")
                line_start, line_end = self._get_line_range(node)
                signature = extract_signature(
                    self._get_node_text(node, source_code), symbol_type, "csharp"
                )
                raw_code = self._get_node_text(node, source_code)

                # Check if this is a constant
                if symbol_type == SymbolType.FIELD and "const" in raw_code.lower():
                    symbol_type = SymbolType.CONSTANT

                symbol = Symbol(
                    id=uuid4(),
                    project_id=project_id,
                    file_path=str(
                        file_path.relative_to(file_path.parents[2])
                    ),  # Relative to project root
                    symbol_type=symbol_type,
                    name=name,
                    qualified_name=qualified_name,
                    signature=signature,
                    line_start=line_start,
                    line_end=line_end,
                    raw_code=raw_code,
                    content_hash=Symbol.generate_content_hash(raw_code),
                    has_todo=self._has_todo_near_node(node, source_code),
                )

                symbols.append(symbol)

        # Determine the parent name for children
        next_parent = qualified_name if (symbol_type and name) else parent_name

        # Recursively check child nodes
        for child in node.children:
            self._extract_from_node(
                child, source_code, file_path, project_id, symbols, next_parent
            )

    def _get_symbol_name(
        self, node: tree_sitter.Node, source_code: str
    ) -> Optional[str]:
        """Extract symbol name from C# node."""
        if node.type in [
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
        ]:
            # Find the identifier node
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)

        elif node.type in ["method_declaration", "constructor_declaration"]:
            # Find the identifier in the header
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)

        elif node.type == "field_declaration":
            # Find the variable_declaration child
            for child in node.children:
                if child.type == "variable_declaration":
                    # Find the variable_declarator child
                    for subchild in child.children:
                        if subchild.type == "variable_declarator":
                            # Find the identifier child
                            for leaf in subchild.children:
                                if leaf.type == "identifier":
                                    return self._get_node_text(leaf, source_code)

        elif node.type == "property_declaration":
            # Get the first variable name
            for child in node.children:
                if child.type == "variable_declarator":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            return self._get_node_text(subchild, source_code)

        return None


class JavaExtractor(SymbolExtractor):
    """Java symbol extractor."""

    def __init__(self) -> None:
        super().__init__("java")

    def _extract_from_node(
        self,
        node: tree_sitter.Node,
        source_code: str,
        file_path: Path,
        project_id: str,
        symbols: List[Symbol],
        parent_name: str = "",
    ) -> None:
        """Extract symbols from Java AST."""
        node_type = node.type
        symbol_type = normalize_symbol_type(node_type, "java")

        name = None
        qualified_name = parent_name

        if symbol_type:
            name = self._get_symbol_name(node, source_code)
            if name:
                qualified_name = build_qualified_name([parent_name, name], "java")
                line_start, line_end = self._get_line_range(node)
                signature = extract_signature(
                    self._get_node_text(node, source_code), symbol_type, "java"
                )
                raw_code = self._get_node_text(node, source_code)

                # Check if this is a constant
                if symbol_type == SymbolType.FIELD and (
                    "static" in raw_code.lower() and "final" in raw_code.lower()
                ):
                    symbol_type = SymbolType.CONSTANT

                symbol = Symbol(
                    id=uuid4(),
                    project_id=project_id,
                    file_path=str(file_path.relative_to(file_path.parents[2])),
                    symbol_type=symbol_type,
                    name=name,
                    qualified_name=qualified_name,
                    signature=signature,
                    line_start=line_start,
                    line_end=line_end,
                    raw_code=raw_code,
                    content_hash=Symbol.generate_content_hash(raw_code),
                    has_todo=self._has_todo_near_node(node, source_code),
                )

                symbols.append(symbol)

        # Determine the parent name for children
        next_parent = qualified_name if (symbol_type and name) else parent_name

        # Recursively check child nodes
        for child in node.children:
            self._extract_from_node(
                child, source_code, file_path, project_id, symbols, next_parent
            )

    def _get_symbol_name(
        self, node: tree_sitter.Node, source_code: str
    ) -> Optional[str]:
        """Extract symbol name from Java node."""
        if node.type in [
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
        ]:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)

        elif node.type in ["method_declaration", "constructor_declaration"]:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)

        elif node.type == "field_declaration":
            # Find variable_declarator
            for child in node.children:
                if child.type == "variable_declarator":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            return self._get_node_text(subchild, source_code)

        return None


class PythonExtractor(SymbolExtractor):
    """Python symbol extractor."""

    def __init__(self) -> None:
        super().__init__("python")

    def _extract_from_node(
        self,
        node: tree_sitter.Node,
        source_code: str,
        file_path: Path,
        project_id: str,
        symbols: List[Symbol],
        parent_name: str = "",
    ) -> None:
        """Extract symbols from Python AST."""
        node_type = node.type
        symbol_type = normalize_symbol_type(node_type, "python")

        name = None
        qualified_name = parent_name

        if symbol_type:
            name = self._get_symbol_name(node, source_code)
            if name:
                qualified_name = build_qualified_name([parent_name, name], "python")
                line_start, line_end = self._get_line_range(node)
                signature = extract_signature(
                    self._get_node_text(node, source_code), symbol_type, "python"
                )
                raw_code = self._get_node_text(node, source_code)

                # Check if this is a constant
                if symbol_type == SymbolType.VARIABLE and is_constant_symbol(
                    name, "python"
                ):
                    symbol_type = SymbolType.CONSTANT

                symbol = Symbol(
                    id=uuid4(),
                    project_id=project_id,
                    file_path=str(file_path.relative_to(file_path.parents[2])),
                    symbol_type=symbol_type,
                    name=name,
                    qualified_name=qualified_name,
                    signature=signature,
                    line_start=line_start,
                    line_end=line_end,
                    raw_code=raw_code,
                    content_hash=Symbol.generate_content_hash(raw_code),
                    has_todo=self._has_todo_near_node(node, source_code),
                )

                symbols.append(symbol)

        # Determine the parent name for children
        next_parent = qualified_name if (symbol_type and name) else parent_name

        # Recursively check child nodes
        for child in node.children:
            self._extract_from_node(
                child, source_code, file_path, project_id, symbols, next_parent
            )

    def _get_symbol_name(
        self, node: tree_sitter.Node, source_code: str
    ) -> Optional[str]:
        """Extract symbol name from Python node."""
        if node.type in [
            "class_definition",
            "function_definition",
            "async_function_definition",
        ]:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)

        elif node.type == "assignment":
            # Check if this is a constant assignment
            for child in node.children:
                if child.type == "identifier":
                    name = self._get_node_text(child, source_code)
                    if is_constant_symbol(name, "python"):
                        return name

        return None


class JavaScriptExtractor(SymbolExtractor):
    """JavaScript/TypeScript symbol extractor."""

    def __init__(self) -> None:
        super().__init__("javascript")

    def _extract_from_node(
        self,
        node: tree_sitter.Node,
        source_code: str,
        file_path: Path,
        project_id: str,
        symbols: List[Symbol],
        parent_name: str = "",
    ) -> None:
        """Extract symbols from JavaScript AST."""
        node_type = node.type
        symbol_type = normalize_symbol_type(node_type, "javascript")

        name = None
        qualified_name = parent_name

        if symbol_type:
            name = self._get_symbol_name(node, source_code)
            if name:
                qualified_name = build_qualified_name([parent_name, name], "javascript")
                line_start, line_end = self._get_line_range(node)
                signature = extract_signature(
                    self._get_node_text(node, source_code), symbol_type, "javascript"
                )
                raw_code = self._get_node_text(node, source_code)

                symbol = Symbol(
                    id=uuid4(),
                    project_id=project_id,
                    file_path=str(file_path.relative_to(file_path.parents[2])),
                    symbol_type=symbol_type,
                    name=name,
                    qualified_name=qualified_name,
                    signature=signature,
                    line_start=line_start,
                    line_end=line_end,
                    raw_code=raw_code,
                    content_hash=Symbol.generate_content_hash(raw_code),
                    has_todo=self._has_todo_near_node(node, source_code),
                )

                symbols.append(symbol)

        # Determine the parent name for children
        next_parent = qualified_name if (symbol_type and name) else parent_name

        # Recursively check child nodes
        for child in node.children:
            self._extract_from_node(
                child, source_code, file_path, project_id, symbols, next_parent
            )

    def _get_symbol_name(
        self, node: tree_sitter.Node, source_code: str
    ) -> Optional[str]:
        """Extract symbol name from JavaScript node."""
        if node.type in ["class_declaration", "function_declaration"]:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)

        elif node.type == "method_definition":
            # For class methods, identifier might be property_identifier or identifier
            for child in node.children:
                if child.type in ["property_identifier", "identifier"]:
                    return self._get_node_text(child, source_code)

        elif node.type == "variable_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            return self._get_node_text(subchild, source_code)

        return None


class RenPyExtractor(SymbolExtractor):
    """RenPy symbol extractor (custom implementation)."""

    def __init__(self) -> None:
        # Don't call parent constructor since RenPy doesn't use tree-sitter
        pass

    def extract_symbols(self, file_path: Path, project_id: str) -> List[Symbol]:
        """Extract symbols from RenPy script using regex."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            symbols = []
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                line = line.strip()

                # Extract labels
                if line.startswith("label "):
                    label_match = re.match(r"label\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                    if label_match:
                        name = label_match.group(1)
                        symbol = Symbol(
                            id=uuid4(),
                            project_id=project_id,
                            file_path=str(file_path.relative_to(file_path.parents[2])),
                            symbol_type=SymbolType.FUNCTION,
                            name=name,
                            qualified_name=name,
                            signature=line,
                            line_start=i,
                            line_end=i,
                            raw_code=line,
                            content_hash=Symbol.generate_content_hash(line),
                            has_todo=detect_todo_comments(line),
                        )
                        symbols.append(symbol)

                # Extract characters
                elif line.startswith("define "):
                    char_match = re.match(
                        r"define\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*Character", line
                    )
                    if char_match:
                        name = char_match.group(1)
                        symbol = Symbol(
                            id=uuid4(),
                            project_id=project_id,
                            file_path=str(file_path.relative_to(file_path.parents[2])),
                            symbol_type=SymbolType.CLASS,
                            name=name,
                            qualified_name=name,
                            signature=line,
                            line_start=i,
                            line_end=i,
                            raw_code=line,
                            content_hash=Symbol.generate_content_hash(line),
                            has_todo=detect_todo_comments(line),
                        )
                        symbols.append(symbol)

            return symbols

        except Exception as e:
            raise ParsingError(f"Failed to parse RenPy file {file_path}: {e}")


# Factory function to get appropriate extractor
def get_extractor(language: str) -> SymbolExtractor:
    """Get the appropriate symbol extractor for a language."""
    language = language.lower()

    if language in ["csharp", "c#"]:
        return CSharpExtractor()
    elif language == "java":
        return JavaExtractor()
    elif language == "python":
        return PythonExtractor()
    elif language in ["javascript", "typescript", "js", "ts"]:
        return JavaScriptExtractor()
    elif language == "renpy":
        return RenPyExtractor()
    else:
        raise ParsingError(f"Unsupported language: {language}")
