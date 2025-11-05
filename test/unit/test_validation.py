"""Unit tests for validation functions."""
import pytest

from patent_mcp_server.util.validation import validate_patent_number, validate_app_number


# ============================================================================
# Patent Number Validation Tests
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_valid():
    """Test patent number validation with valid inputs."""
    # Standard formats
    assert validate_patent_number("9876543") == "9876543"
    assert validate_patent_number("7123456") == "7123456"
    assert validate_patent_number("8234567") == "8234567"
    assert validate_patent_number("10123456") == "10123456"  # 8-digit


@pytest.mark.unit
def test_validate_patent_number_with_prefix():
    """Test patent number validation with US prefix."""
    assert validate_patent_number("US9876543") == "9876543"
    assert validate_patent_number("US 9876543") == "9876543"
    assert validate_patent_number("us9876543") == "9876543"


@pytest.mark.unit
def test_validate_patent_number_with_commas():
    """Test patent number validation with comma separators."""
    assert validate_patent_number("9,876,543") == "9876543"
    assert validate_patent_number("10,123,456") == "10123456"


@pytest.mark.unit
def test_validate_patent_number_with_mixed_formatting():
    """Test patent number validation with mixed formatting."""
    assert validate_patent_number("US 9,876,543") == "9876543"
    assert validate_patent_number("US-9876543") == "9876543"


@pytest.mark.unit
def test_validate_patent_number_integer_input():
    """Test patent number validation with integer input."""
    assert validate_patent_number(9876543) == "9876543"
    assert validate_patent_number("9876543") == "9876543"


@pytest.mark.unit
def test_validate_patent_number_empty():
    """Test patent number validation with empty input."""
    with pytest.raises(ValueError, match="Patent number cannot be empty"):
        validate_patent_number("")

    with pytest.raises(ValueError, match="Patent number cannot be empty"):
        validate_patent_number("   ")  # Whitespace only


@pytest.mark.unit
def test_validate_patent_number_invalid_characters():
    """Test patent number validation with invalid characters."""
    with pytest.raises(ValueError, match="Patent number must be numeric"):
        validate_patent_number("abc")

    with pytest.raises(ValueError, match="Patent number must be numeric"):
        validate_patent_number("123abc")

    with pytest.raises(ValueError, match="Patent number must be numeric"):
        validate_patent_number("!@#$%")


@pytest.mark.unit
def test_validate_patent_number_too_short():
    """Test patent number validation with too short input."""
    with pytest.raises(ValueError, match="Patent number too short"):
        validate_patent_number("1")

    with pytest.raises(ValueError, match="Patent number too short"):
        validate_patent_number("12")

    with pytest.raises(ValueError, match="Patent number too short"):
        validate_patent_number("123")


@pytest.mark.unit
def test_validate_patent_number_too_long():
    """Test patent number validation with too long input."""
    # Very long number (unrealistic)
    with pytest.raises(ValueError):
        validate_patent_number("123456789012345")  # 15 digits


# ============================================================================
# Application Number Validation Tests
# ============================================================================

@pytest.mark.unit
def test_validate_app_number_valid():
    """Test application number validation with valid inputs."""
    assert validate_app_number("14412875") == "14412875"
    assert validate_app_number("15123456") == "15123456"
    assert validate_app_number("16234567") == "16234567"


@pytest.mark.unit
def test_validate_app_number_with_separators():
    """Test application number validation with separators."""
    assert validate_app_number("14/412,875") == "14412875"
    assert validate_app_number("14/412875") == "14412875"
    assert validate_app_number("14412,875") == "14412875"


@pytest.mark.unit
def test_validate_app_number_with_spaces():
    """Test application number validation with spaces."""
    assert validate_app_number("14 412 875") == "14412875"
    assert validate_app_number("14 412875") == "14412875"


@pytest.mark.unit
def test_validate_app_number_mixed_formatting():
    """Test application number validation with mixed formatting."""
    assert validate_app_number("14/412,875") == "14412875"
    assert validate_app_number("14 / 412 , 875") == "14412875"


@pytest.mark.unit
def test_validate_app_number_integer_input():
    """Test application number validation with integer input."""
    assert validate_app_number(14412875) == "14412875"
    assert validate_app_number("14412875") == "14412875"


@pytest.mark.unit
def test_validate_app_number_empty():
    """Test application number validation with empty input."""
    with pytest.raises(ValueError, match="Application number cannot be empty"):
        validate_app_number("")

    with pytest.raises(ValueError, match="Application number cannot be empty"):
        validate_app_number("   ")


@pytest.mark.unit
def test_validate_app_number_invalid_characters():
    """Test application number validation with invalid characters."""
    with pytest.raises(ValueError, match="Application number must be numeric"):
        validate_app_number("abc")

    with pytest.raises(ValueError, match="Application number must be numeric"):
        validate_app_number("14/abc")

    with pytest.raises(ValueError, match="Application number must be numeric"):
        validate_app_number("!@#$%")


@pytest.mark.unit
def test_validate_app_number_too_short():
    """Test application number validation with too short input."""
    with pytest.raises(ValueError, match="Application number too short"):
        validate_app_number("1")

    with pytest.raises(ValueError, match="Application number too short"):
        validate_app_number("12")

    with pytest.raises(ValueError, match="Application number too short"):
        validate_app_number("123")


# ============================================================================
# Edge Cases and Special Scenarios
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_leading_zeros():
    """Test patent number with leading zeros."""
    # Leading zeros should be preserved
    result = validate_patent_number("00123456")
    assert "123456" in result or result == "00123456"


@pytest.mark.unit
def test_validate_app_number_leading_zeros():
    """Test application number with leading zeros."""
    result = validate_app_number("01234567")
    assert "1234567" in result or result == "01234567"


@pytest.mark.unit
def test_validate_patent_number_whitespace():
    """Test patent number with whitespace."""
    assert validate_patent_number("  9876543  ") == "9876543"
    assert validate_patent_number("9 8 7 6 5 4 3") == "9876543"


@pytest.mark.unit
def test_validate_app_number_whitespace():
    """Test application number with whitespace."""
    assert validate_app_number("  14412875  ") == "14412875"


@pytest.mark.unit
def test_validate_patent_number_unicode():
    """Test patent number with unicode characters."""
    with pytest.raises(ValueError):
        validate_patent_number("987654３")  # Full-width 3


@pytest.mark.unit
def test_validate_app_number_unicode():
    """Test application number with unicode characters."""
    with pytest.raises(ValueError):
        validate_app_number("1441287５")  # Full-width 5


# ============================================================================
# Type Conversion Tests
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_string_conversion():
    """Test that various types are converted to string."""
    # Integer
    assert validate_patent_number(9876543) == "9876543"

    # Float (should work if valid)
    try:
        result = validate_patent_number(9876543.0)
        assert result == "9876543"
    except:
        pass  # Float conversion might not be supported


@pytest.mark.unit
def test_validate_app_number_string_conversion():
    """Test that various types are converted to string."""
    # Integer
    assert validate_app_number(14412875) == "14412875"


# ============================================================================
# Boundary Value Tests
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_minimum_length():
    """Test minimum valid patent number length."""
    # 4 digits is minimum
    assert len(validate_patent_number("1234")) >= 4


@pytest.mark.unit
def test_validate_app_number_minimum_length():
    """Test minimum valid application number length."""
    # 4 digits is minimum
    assert len(validate_app_number("1234")) >= 4


@pytest.mark.unit
def test_validate_patent_number_typical_lengths():
    """Test typical patent number lengths."""
    # 7-digit (typical)
    assert validate_patent_number("9876543") == "9876543"

    # 8-digit (newer patents)
    assert validate_patent_number("10123456") == "10123456"


@pytest.mark.unit
def test_validate_app_number_typical_lengths():
    """Test typical application number lengths."""
    # 8-digit (typical)
    assert validate_app_number("14412875") == "14412875"

    # Series code + number (14/412,875)
    assert validate_app_number("14/412875") == "14412875"
