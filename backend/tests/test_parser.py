"""Tests for parser layer (tree-sitter extractors)."""

import pytest
from pathlib import Path
from uuid import uuid4

from vault.parser.extractors import (
    CSharpExtractor,
    JavaExtractor,
    PythonExtractor,
    JavaScriptExtractor,
    RenPyExtractor,
    get_extractor,
)
from vault.exceptions import ParsingError
from vault.parser.symbol_types import SymbolType
from vault.storage.models import Symbol


def skip_if_parser_unavailable(extractor_class, language_name: str):
    """Skip test if the tree-sitter parser for the language is not available."""
    try:
        extractor_class()
    except ParsingError as e:
        if f"tree_sitter_{language_name}" in str(e):
            pytest.skip(f"{language_name.title()} tree-sitter parser not available in CI environment")


class TestCSharpExtractor:
    """Test cases for C# symbol extractor."""
    
    def test_extract_class_symbols(self, temp_project_dir: Path, csharp_sample_files: dict[str, str]):
        """Test extracting C# class symbols."""
        skip_if_parser_unavailable(CSharpExtractor, "csharp")
        
        # Create test file
        test_file = temp_project_dir / "TestClass.cs"
        test_file.write_text(csharp_sample_files["TestClass.cs"])
        
        extractor = CSharpExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        # Should extract the class and its members
        class_symbols = [s for s in symbols if s.symbol_type == SymbolType.CLASS]
        method_symbols = [s for s in symbols if s.symbol_type == SymbolType.METHOD]
        field_symbols = [s for s in symbols if s.symbol_type == SymbolType.FIELD]
        
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "TestClass"
        
        assert len(method_symbols) + len([s for s in symbols if s.symbol_type == SymbolType.CONSTRUCTOR]) >= 2
        method_names = {s.name for s in symbols if s.symbol_type in [SymbolType.METHOD, SymbolType.CONSTRUCTOR]}
        assert "TestClass" in method_names  # Constructor
        assert "GetName" in method_names
        
        assert len(field_symbols) == 1
        assert field_symbols[0].name == "_name"
    
    def test_extract_interface_symbols(self, temp_project_dir: Path, csharp_sample_files: dict[str, str]):
        """Test extracting C# interface symbols."""
        skip_if_parser_unavailable(CSharpExtractor, "csharp")
        test_file = temp_project_dir / "IInterface.cs"
        test_file.write_text(csharp_sample_files["IInterface.cs"])
        
        extractor = CSharpExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        interface_symbols = [s for s in symbols if s.symbol_type == SymbolType.INTERFACE]
        assert len(interface_symbols) == 1
        assert interface_symbols[0].name == "IInterface"
    
    def test_extract_constant_symbols(self, temp_project_dir: Path, csharp_sample_files: dict[str, str]):
        """Test extracting C# constant symbols."""
        skip_if_parser_unavailable(CSharpExtractor, "csharp")
        test_file = temp_project_dir / "Constants.cs"
        test_file.write_text(csharp_sample_files["Constants.cs"])
        
        extractor = CSharpExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        constant_symbols = [s for s in symbols if s.symbol_type == SymbolType.CONSTANT]
        assert len(constant_symbols) >= 2
        
        constant_names = {s.name for s in constant_symbols}
        assert "DEFAULT_NAME" in constant_names
        assert "MAX_LENGTH" in constant_names
    
    def test_detect_todo_comments(self, temp_project_dir: Path, csharp_sample_files: dict[str, str]):
        """Test detecting TODO comments in C# code."""
        skip_if_parser_unavailable(CSharpExtractor, "csharp")
        test_file = temp_project_dir / "TestClass.cs"
        test_file.write_text(csharp_sample_files["TestClass.cs"])
        
        extractor = CSharpExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        todo_symbols = [s for s in symbols if s.has_todo]
        assert len(todo_symbols) >= 1
        
        # Check that the method with TODO is marked
        set_name_method = next((s for s in symbols if s.name == "SetName"), None)
        assert set_name_method is not None
        assert set_name_method.has_todo is True


class TestJavaExtractor:
    """Test cases for Java symbol extractor."""
    
    def test_extract_class_symbols(self, temp_project_dir: Path, java_sample_files: dict[str, str]):
        """Test extracting Java class symbols."""
        skip_if_parser_unavailable(JavaExtractor, "java")
        
        test_file = temp_project_dir / "TestClass.java"
        test_file.write_text(java_sample_files["TestClass.java"])
        
        extractor = JavaExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        class_symbols = [s for s in symbols if s.symbol_type == SymbolType.CLASS]
        method_symbols = [s for s in symbols if s.symbol_type == SymbolType.METHOD]
        field_symbols = [s for s in symbols if s.symbol_type == SymbolType.FIELD]
        
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "TestClass"
        
        assert len(method_symbols) + len([s for s in symbols if s.symbol_type == SymbolType.CONSTRUCTOR]) >= 2
        method_names = {s.name for s in symbols if s.symbol_type in [SymbolType.METHOD, SymbolType.CONSTRUCTOR]}
        assert "TestClass" in method_names  # Constructor
        assert "getName" in method_names
        
        assert len(field_symbols) == 1
        assert field_symbols[0].name == "name"
    
    def test_extract_interface_symbols(self, temp_project_dir: Path, java_sample_files: dict[str, str]):
        """Test extracting Java interface symbols."""
        skip_if_parser_unavailable(JavaExtractor, "java")
        test_file = temp_project_dir / "Interface.java"
        test_file.write_text(java_sample_files["Interface.java"])
        
        extractor = JavaExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        interface_symbols = [s for s in symbols if s.symbol_type == SymbolType.INTERFACE]
        assert len(interface_symbols) == 1
        assert interface_symbols[0].name == "Interface"
    
    def test_extract_constant_symbols(self, temp_project_dir: Path, java_sample_files: dict[str, str]):
        """Test extracting Java constant symbols."""
        skip_if_parser_unavailable(JavaExtractor, "java")
        test_file = temp_project_dir / "Constants.java"
        test_file.write_text(java_sample_files["Constants.java"])
        
        extractor = JavaExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        constant_symbols = [s for s in symbols if s.symbol_type == SymbolType.CONSTANT]
        assert len(constant_symbols) >= 2
        
        constant_names = {s.name for s in constant_symbols}
        assert "DEFAULT_NAME" in constant_names
        assert "MAX_LENGTH" in constant_names


class TestPythonExtractor:
    """Test cases for Python symbol extractor."""
    
    def test_extract_class_symbols(self, temp_project_dir: Path, python_sample_files: dict[str, str]):
        """Test extracting Python class symbols."""
        skip_if_parser_unavailable(PythonExtractor, "python")
        test_file = temp_project_dir / "test_class.py"
        test_file.write_text(python_sample_files["test_class.py"])
        
        extractor = PythonExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        class_symbols = [s for s in symbols if s.symbol_type == SymbolType.CLASS]
        function_symbols = [s for s in symbols if s.symbol_type == SymbolType.FUNCTION]
        constant_symbols = [s for s in symbols if s.symbol_type == SymbolType.CONSTANT]
        
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "TestClass"
        
        assert len(function_symbols) >= 2  # __init__ and get_name
        function_names = {s.name for s in function_symbols}
        assert "__init__" in function_names
        assert "get_name" in function_names
        
        assert len(constant_symbols) == 1
        assert constant_symbols[0].name == "MAX_LENGTH"
    
    def test_detect_constants(self, temp_project_dir: Path, python_sample_files: dict[str, str]):
        """Test detecting Python constants."""
        skip_if_parser_unavailable(PythonExtractor, "python")
        test_file = temp_project_dir / "constants.py"
        test_file.write_text(python_sample_files["constants.py"])
        
        extractor = PythonExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        constant_symbols = [s for s in symbols if s.symbol_type == SymbolType.CONSTANT]
        assert len(constant_symbols) >= 2
        
        constant_names = {s.name for s in constant_symbols}
        assert "DEFAULT_NAME" in constant_names
        assert "VERSION" in constant_names


class TestJavaScriptExtractor:
    """Test cases for JavaScript symbol extractor."""
    
    def test_extract_class_symbols(self, temp_project_dir: Path, javascript_sample_files: dict[str, str]):
        """Test extracting JavaScript class symbols."""
        skip_if_parser_unavailable(JavaScriptExtractor, "javascript")
        test_file = temp_project_dir / "TestClass.js"
        test_file.write_text(javascript_sample_files["TestClass.js"])
        
        extractor = JavaScriptExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        class_symbols = [s for s in symbols if s.symbol_type == SymbolType.CLASS]
        function_symbols = [s for s in symbols if s.symbol_type == SymbolType.FUNCTION]
        
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "TestClass"
        
        assert len(function_symbols) + len([s for s in symbols if s.symbol_type == SymbolType.METHOD]) >= 2  # constructor and getName
        function_names = {s.name for s in symbols if s.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD]}
        assert "constructor" in function_names or "TestClass" in function_names
        assert "getName" in function_names
    
    def test_extract_function_symbols(self, temp_project_dir: Path, javascript_sample_files: dict[str, str]):
        """Test extracting JavaScript function symbols."""
        skip_if_parser_unavailable(JavaScriptExtractor, "javascript")
        test_file = temp_project_dir / "TestClass.js"
        test_file.write_text(javascript_sample_files["TestClass.js"])
        
        extractor = JavaScriptExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        # Should extract standalone function
        standalone_functions = [s for s in symbols if s.symbol_type == SymbolType.FUNCTION and s.name == "testFunction"]
        assert len(standalone_functions) == 1


class TestRenPyExtractor:
    """Test cases for RenPy symbol extractor."""
    
    def test_extract_label_symbols(self, temp_project_dir: Path, renpy_sample_files: dict[str, str]):
        """Test extracting RenPy label symbols."""
        test_file = temp_project_dir / "script.rpy"
        test_file.write_text(renpy_sample_files["script.rpy"])
        
        extractor = RenPyExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        label_symbols = [s for s in symbols if s.symbol_type == SymbolType.FUNCTION]
        assert len(label_symbols) >= 2
        
        label_names = {s.name for s in label_symbols}
        assert "start" in label_names
        assert "ending" in label_names
    
    def test_extract_character_symbols(self, temp_project_dir: Path, renpy_sample_files: dict[str, str]):
        """Test extracting RenPy character symbols."""
        test_file = temp_project_dir / "script.rpy"
        test_file.write_text(renpy_sample_files["script.rpy"])
        
        extractor = RenPyExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        character_symbols = [s for s in symbols if s.symbol_type == SymbolType.CLASS]
        assert len(character_symbols) >= 1
        
        character_names = {s.name for s in character_symbols}
        assert "e" in character_names


class TestExtractorFactory:
    """Test cases for the extractor factory function."""
    
    def test_get_csharp_extractor(self):
        """Test getting C# extractor."""
        skip_if_parser_unavailable(CSharpExtractor, "csharp")
        extractor = get_extractor("csharp")
        assert isinstance(extractor, CSharpExtractor)
        
        extractor = get_extractor("c#")
        assert isinstance(extractor, CSharpExtractor)
    
    def test_get_java_extractor(self):
        """Test getting Java extractor."""
        skip_if_parser_unavailable(JavaExtractor, "java")
        extractor = get_extractor("java")
        assert isinstance(extractor, JavaExtractor)
    
    def test_get_python_extractor(self):
        """Test getting Python extractor."""
        skip_if_parser_unavailable(PythonExtractor, "python")
        extractor = get_extractor("python")
        assert isinstance(extractor, PythonExtractor)
    
    def test_get_javascript_extractor(self):
        """Test getting JavaScript extractor."""
        skip_if_parser_unavailable(JavaScriptExtractor, "javascript")
        extractor = get_extractor("javascript")
        assert isinstance(extractor, JavaScriptExtractor)
        
        extractor = get_extractor("js")
        assert isinstance(extractor, JavaScriptExtractor)
        
        extractor = get_extractor("typescript")
        assert isinstance(extractor, JavaScriptExtractor)
    
    def test_get_renpy_extractor(self):
        """Test getting RenPy extractor."""
        extractor = get_extractor("renpy")
        assert isinstance(extractor, RenPyExtractor)
    
    def test_unsupported_language(self):
        """Test getting extractor for unsupported language."""
        with pytest.raises(ParsingError, match="Unsupported language"):
            get_extractor("unsupported")


class TestSymbolExtractionIntegration:
    """Integration tests for symbol extraction."""
    
    def test_extract_symbols_from_empty_file(self, temp_project_dir: Path):
        """Test extracting symbols from an empty file."""
        test_file = temp_project_dir / "empty.py"
        test_file.write_text("")
        
        extractor = PythonExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        assert len(symbols) == 0
    
    def test_extract_symbols_from_malformed_file(self, temp_project_dir: Path):
        """Test extracting symbols from malformed code."""
        test_file = temp_project_dir / "malformed.py"
        test_file.write_text("def incomplete_function(")
        
        extractor = PythonExtractor()
        # Should not raise an exception, but return empty or partial results
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        # May return empty or partial symbols, but should not crash
        assert isinstance(symbols, list)
    
    def test_content_hash_generation(self, temp_project_dir: Path, python_sample_files: dict[str, str]):
        """Test content hash generation for change detection."""
        test_file = temp_project_dir / "test_class.py"
        content = python_sample_files["test_class.py"]
        test_file.write_text(content)
        
        extractor = PythonExtractor()
        symbols = extractor.extract_symbols(test_file, str(uuid4()))
        
        # All symbols should have content hashes
        for symbol in symbols:
            assert symbol.content_hash is not None
            assert len(symbol.content_hash) == 32  # MD5 hash length
        
        # Same content should produce same hash
        symbols2 = extractor.extract_symbols(test_file, str(uuid4()))
        for s1, s2 in zip(symbols, symbols2):
            assert s1.content_hash == s2.content_hash
        
        # Different content should produce different hash (add comment inside class)
        content_lines = content.split("\n")
        content_lines.insert(2, "    # Added comment inside class")
        test_file.write_text("\n".join(content_lines))
        symbols3 = extractor.extract_symbols(test_file, str(uuid4()))
        # Only symbols whose raw_code changed should have different hash
        for s1, s3 in zip(symbols, symbols3):
            if s1.name == "TestClass":
                assert s1.content_hash != s3.content_hash
            elif s1.name == "__init__":
                # __init__ hasn't changed if comment is above it
                assert s1.content_hash == s3.content_hash
