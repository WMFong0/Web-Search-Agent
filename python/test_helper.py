import pytest
from helper import _stringify_input, _format_response


# ================================
# Tests for _stringify_input
# ================================

def test_stringify_input_single_product():
    """Test _stringify_input with a single product."""
    user_input = [
        ["Product A", "Description A", "Usage A"]
    ]
    result = _stringify_input(user_input)
    assert result == "Product 1:\n\nName: Product A\nDescription: Description A\nUsage: Usage A"


def test_stringify_input_multiple_products():
    """Test _stringify_input with multiple products."""
    user_input = [
        ["Product A", "Description A", "Usage A"],
        ["Product B", "Description B", "Usage B"]
    ]
    result = _stringify_input(user_input)
    expected = "Product 1:\n\nName: Product A\nDescription: Description A\nUsage: Usage A\n\n\nProduct 2:\n\nName: Product B\nDescription: Description B\nUsage: Usage B"
    assert result == expected


def test_stringify_input_empty_list():
    """Test _stringify_input with an empty list."""
    user_input = []
    result = _stringify_input(user_input)
    assert result == ""


def test_stringify_input_with_chinese_characters():
    """Test _stringify_input with Chinese characters (like the example in helper.py)."""
    user_input = [
        ["極潤潔面泡沬", "溫和潔淨肌膚", "取適量於手掌"],
        ["黑頭火山泥潔面乳", "改善易長痘肌膚", "將產品塗抹於濕潤的面部"]
    ]
    result = _stringify_input(user_input)
    assert "Product 1:" in result
    assert "Product 2:" in result
    assert "極潤潔面泡沬" in result
    assert "黑頭火山泥潔面乳" in result
    assert "\n\n\n" in result  # Separator between products


def test_stringify_input_with_multiline_strings():
    """Test _stringify_input with multiline description and usage."""
    user_input = [
        ["Product", "Line 1\nLine 2\nLine 3", "Usage 1\nUsage 2"]
    ]
    result = _stringify_input(user_input)
    assert "Product 1:" in result
    assert "Line 1\nLine 2\nLine 3" in result
    assert "Usage 1\nUsage 2" in result


def test_stringify_input_three_products():
    """Test _stringify_input with three products."""
    user_input = [
        ["P1", "D1", "U1"],
        ["P2", "D2", "U2"],
        ["P3", "D3", "U3"]
    ]
    result = _stringify_input(user_input)
    assert result.count("Product") == 3
    assert result.count("\n\n\n") == 2  # 2 separators between 3 products


# ================================
# Tests for _format_response
# ================================

def test_format_response_single_item():
    """Test _format_response with a single item (no commas)."""
    response = "Item 1"
    result = _format_response(response)
    assert result == "Item 1"


def test_format_response_comma_separated():
    """Test _format_response with comma-separated values."""
    response = "Item 1, Item 2, Item 3"
    result = _format_response(response)
    assert result == "Item 1"  # Should return the first item


def test_format_response_with_newlines():
    """Test _format_response removes newlines."""
    response = "Item 1,\nItem 2,\nItem 3"
    result = _format_response(response)
    assert result == "Item 1"


def test_format_response_with_extra_spaces():
    """Test _format_response handles extra spaces correctly."""
    response = "  Item 1  ,   Item 2  ,   Item 3  "
    result = _format_response(response)
    assert result == "Item 1"


def test_format_response_empty_string():
    """Test _format_response with an empty string."""
    response = ""
    result = _format_response(response)
    assert result is None


def test_format_response_only_whitespace():
    """Test _format_response with only whitespace."""
    response = "   \n\t  "
    result = _format_response(response)
    assert result is None


def test_format_response_comma_without_items():
    """Test _format_response with only commas."""
    response = ",,,"
    result = _format_response(response)
    assert result is None


def test_format_response_mixed_whitespace_and_commas():
    """Test _format_response with mixed whitespace and commas."""
    response = " , , , Item 1 "
    result = _format_response(response)
    assert result == "Item 1"


def test_format_response_single_item_with_newlines():
    """Test _format_response with a single item containing newlines."""
    response = "Item\n1\nDescription"
    result = _format_response(response)
    assert result == "Item1Description"


def test_format_response_multiple_commas_between_items():
    """Test _format_response with multiple commas between items."""
    response = "Item 1,,,Item 2"
    result = _format_response(response)
    assert result == "Item 1"

 
def test_format_response_chinese_characters():
    """Test _format_response with Chinese characters."""
    response = "產品A, 產品B, 產品C"
    result = _format_response(response)
    assert result == "產品A"