"""Tests for vault.parser.symbol_types to improve coverage."""

import pytest
from vault.parser.symbol_types import (
    SymbolType,
    normalize_symbol_type,
    is_constant_symbol,
    get_method_visibility,
    build_qualified_name,
    extract_signature,
    detect_todo_comments
)

def test_normalize_symbol_type():
    # Test JS/TS
    assert normalize_symbol_type("class_declaration", "javascript") == SymbolType.CLASS
    assert normalize_symbol_type("class_declaration", "JS") == SymbolType.CLASS
    assert normalize_symbol_type("class_declaration", "typescript") == SymbolType.CLASS
    assert normalize_symbol_type("class_declaration", "TS") == SymbolType.CLASS
    
    # Test C#
    assert normalize_symbol_type("class_declaration", "csharp") == SymbolType.CLASS
    assert normalize_symbol_type("class_declaration", "c#") == SymbolType.CLASS
    
    # Test Java
    assert normalize_symbol_type("class_declaration", "java") == SymbolType.CLASS
    
    # Test RenPy
    assert normalize_symbol_type("label", "renpy") == SymbolType.FUNCTION
    assert normalize_symbol_type("character", "renpy") == SymbolType.CLASS
    
    # Test Unknown language
    assert normalize_symbol_type("class", "unknown") is None
    
    # Test mapping with None
    assert normalize_symbol_type("unknown_node", "python") is None

def test_is_constant_symbol():
    # Test Python const
    assert is_constant_symbol("MAX_SIZE", "python") is True
    assert is_constant_symbol("max_size", "python") is False
    
    # Test JS const
    assert is_constant_symbol("VERSION", "javascript") is True
    
    # Test Java/C# (always False as they have explicit modifiers)
    assert is_constant_symbol("CONST", "java") is False
    assert is_constant_symbol("CONST", "csharp") is False
    
    # Test Unknown language
    assert is_constant_symbol("CONST", "other") is False

def test_get_method_visibility():
    # Test Java/C#
    assert get_method_visibility(["private"], "java") == "private"
    assert get_method_visibility(["protected"], "csharp") == "protected"
    assert get_method_visibility(["public"], "java") == "public"
    assert get_method_visibility(["static"], "java") == "package"
    assert get_method_visibility(["static"], "csharp") == "internal"
    
    # Test JS/TS
    assert get_method_visibility(["private"], "javascript") == "public"
    
    # Test Python
    assert get_method_visibility(["_internal"], "python") == "private"
    assert get_method_visibility(["public_method"], "python") == "public"
    
    # Test Empty
    assert get_method_visibility([], "java") == "public"
    
    # Test Other
    assert get_method_visibility(["any"], "other") == "public"

def test_build_qualified_name():
    # Test Empty
    assert build_qualified_name([], "java") == ""
    
    # Test Java/C#
    assert build_qualified_name(["N", "C"], "java") == "N.C"
    assert build_qualified_name(["N", "C"], "csharp") == "N.C"
    
    # Test JS/TS
    assert build_qualified_name(["M", "C"], "javascript") == "M.C"
    assert build_qualified_name(["M", "C"], "typescript") == "M.C"
    
    # Test filtering empty parts
    assert build_qualified_name(["A", "", "B"], "python") == "A.B"
    
    # Test other language
    assert build_qualified_name(["A", "B"], "other") == "A.B"

def test_extract_signature():
    # Test Empty
    assert extract_signature("", SymbolType.CLASS, "python") == ""
    assert extract_signature("\n \n", SymbolType.CLASS, "java") == ""
    assert extract_signature("class X:", SymbolType.CLASS, "python") == "class X:"
    
    # Test Function types with different splitters
    func_text = "def foo():\n    pass"
    assert extract_signature(func_text, SymbolType.FUNCTION, "python") == "def foo():"
    
    func_text_no_split = "def foo()\n    pass"
    assert extract_signature(func_text_no_split, SymbolType.FUNCTION, "python") == "def foo()"
    
    # Test Field types
    assert extract_signature("public int x;", SymbolType.FIELD, "java") == "public int x;"
    
    # Test Unknown type
    assert extract_signature("something", SymbolType.VARIABLE, "python") == "something"

def test_detect_todo_comments():
    # Test Empty
    assert detect_todo_comments(None) is False
    assert detect_todo_comments("") is False
    
    # Test Various patterns
    assert detect_todo_comments("// FIXME: fix it") is True
    assert detect_todo_comments("# HACK: work") is True
    assert detect_todo_comments("/* XXX: test */") is True
    assert detect_todo_comments("NOTE: remember") is True
    assert detect_todo_comments("BUG: here") is True
    assert detect_todo_comments("Normal comment") is False
