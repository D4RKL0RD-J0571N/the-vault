"""Tests for vault.parser.extractors to improve coverage."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from vault.parser.extractors import (
    SymbolExtractor, 
    RenPyExtractor, 
    get_extractor,
    CSharpExtractor,
    JavaExtractor,
    PythonExtractor,
    JavaScriptExtractor
)
from vault.exceptions import ParsingError

def test_symbol_extractor_setup_fail():
    # Trigger ParsingError in _setup_parser
    # We can patch get_language or get_parser to raise
    with patch("vault.parser.extractors.get_language", side_effect=Exception("Setup Fail")):
        with pytest.raises(ParsingError, match="Failed to setup parser"):
            SymbolExtractor("unsupported")

def test_symbol_extractor_parse_error():
    # Hit lines 67-68
    with patch.object(SymbolExtractor, "_setup_parser"):
        extractor = SymbolExtractor("python")
        extractor.parser = MagicMock()
        extractor.parser.parse.side_effect = Exception("Parse Fail")
        
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = "print('hello')"
        
        with patch("builtins.open", mock_open):
            with patch("vault.parser.extractors.Path.exists", return_value=True):
                # Need to use a real path or patch open correctly
                with pytest.raises(ParsingError, match="Failed to parse"):
                    extractor.extract_symbols(Path("test.py"), "proj_id")

def test_renpy_extractor_success(tmp_path):
    extractor = RenPyExtractor()
    rpy_file = tmp_path / "test.rpy"
    rpy_file.write_text("""
define e = Character("Eileen")
label start:
    "Hello"
""", encoding="utf-8")
    
    # Need to patch the relative_to call because rpy_file.parents[2] might fail if tmp_path is shallow
    with patch("vault.storage.models.Symbol.__init__", return_value=None):
        with patch("pathlib.Path.relative_to", return_value=Path("test.rpy")):
            symbols = extractor.extract_symbols(rpy_file, "proj_id")
            assert len(symbols) == 2

def test_renpy_extractor_error():
    extractor = RenPyExtractor()
    with pytest.raises(ParsingError, match="Failed to parse RenPy file"):
        extractor.extract_symbols(Path("/non/existent"), "proj_id")

def test_get_extractor_unsupported():
    with pytest.raises(ParsingError, match="Unsupported language"):
        get_extractor("fortran")

def test_extractors_instantiation():
    # Just ensure they can be instantiated if languages are available
    # or mock setup to just hit the __init__
    with patch.object(SymbolExtractor, "_setup_parser"):
        assert isinstance(CSharpExtractor(), CSharpExtractor)
        assert isinstance(JavaExtractor(), JavaExtractor)
        assert isinstance(PythonExtractor(), PythonExtractor)
        assert isinstance(JavaScriptExtractor(), JavaScriptExtractor)
