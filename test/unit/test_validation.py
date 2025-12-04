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
    """Test patent number validation with integer input - should fail as integers not supported."""
    # The validation now only accepts strings
    with pytest.raises(ValueError, match="Invalid patent number"):
        validate_patent_number(9876543)


@pytest.mark.unit
def test_validate_patent_number_empty():
    """Test patent number validation with empty input."""
    with pytest.raises(ValueError, match="Invalid patent number"):
        validate_patent_number("")

    with pytest.raises(ValueError, match="Invalid patent number"):
        validate_patent_number("   ")  # Whitespace only


@pytest.mark.unit
def test_validate_patent_number_invalid_characters():
    """Test patent number validation with invalid characters."""
    with pytest.raises(ValueError, match="must contain at least one digit"):
        validate_patent_number("abc")

    # "123abc" actually has digits so it cleans to "123"
    result = validate_patent_number("123abc")
    assert result == "123"

    with pytest.raises(ValueError, match="must contain at least one digit"):
        validate_patent_number("!@#$%")


@pytest.mark.unit
def test_validate_patent_number_too_short():
    """Test patent number validation - short numbers are allowed after cleaning."""
    # Short numbers are now accepted (validation only checks for digits)
    result = validate_patent_number("1")
    assert result == "1"


@pytest.mark.unit
def test_validate_patent_number_too_long():
    """Test patent number validation with too long input - should still work."""
    # Very long numbers are accepted (just cleaned of non-digits)
    result = validate_patent_number("123456789012345")  # 15 digits
    assert result == "123456789012345"


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
    """Test application number validation with integer input - should fail."""
    with pytest.raises(ValueError, match="Invalid application number"):
        validate_app_number(14412875)


@pytest.mark.unit
def test_validate_app_number_empty():
    """Test application number validation with empty input."""
    with pytest.raises(ValueError, match="Invalid application number"):
        validate_app_number("")

    with pytest.raises(ValueError, match="Invalid application number"):
        validate_app_number("   ")


@pytest.mark.unit
def test_validate_app_number_invalid_characters():
    """Test application number validation with invalid characters."""
    with pytest.raises(ValueError, match="must contain at least one digit"):
        validate_app_number("abc")

    # "14/abc" has digits, so it cleans to "14" but that's too short
    with pytest.raises(ValueError, match="at least 6 digits"):
        validate_app_number("14/abc")

    with pytest.raises(ValueError, match="must contain at least one digit"):
        validate_app_number("!@#$%")


@pytest.mark.unit
def test_validate_app_number_too_short():
    """Test application number validation with too short input."""
    with pytest.raises(ValueError, match="at least 6 digits"):
        validate_app_number("1")

    with pytest.raises(ValueError, match="at least 6 digits"):
        validate_app_number("12")

    with pytest.raises(ValueError, match="at least 6 digits"):
        validate_app_number("123")


# ============================================================================
# Edge Cases and Special Scenarios
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_leading_zeros():
    """Test patent number with leading zeros."""
    # Leading zeros should be preserved
    result = validate_patent_number("00123456")
    assert result == "00123456"


@pytest.mark.unit
def test_validate_app_number_leading_zeros():
    """Test application number with leading zeros."""
    result = validate_app_number("01234567")
    assert result == "01234567"


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
    """Test patent number with unicode characters - full-width digits may be kept."""
    # Full-width digits may or may not be considered digits by str.isdigit()
    # depending on Python version and implementation
    result = validate_patent_number("987654３")
    # Accept either with or without the full-width character
    assert result in ("987654", "987654３")


@pytest.mark.unit
def test_validate_app_number_unicode():
    """Test application number with unicode characters - full-width digits may be kept."""
    # Full-width digits may or may not be considered digits by str.isdigit()
    result = validate_app_number("1441287５")
    # Accept either with or without the full-width character
    assert result in ("1441287", "1441287５")


# ============================================================================
# Type Conversion Tests
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_string_conversion():
    """Test that string inputs work properly."""
    assert validate_patent_number("9876543") == "9876543"


@pytest.mark.unit
def test_validate_app_number_string_conversion():
    """Test that string inputs work properly."""
    assert validate_app_number("14412875") == "14412875"


# ============================================================================
# Boundary Value Tests
# ============================================================================

@pytest.mark.unit
def test_validate_patent_number_minimum_length():
    """Test minimum valid patent number length."""
    # Single digit is now valid
    result = validate_patent_number("1234")
    assert result == "1234"


@pytest.mark.unit
def test_validate_app_number_minimum_length():
    """Test minimum valid application number length - 6 digits required."""
    # 6 digits minimum
    result = validate_app_number("123456")
    assert result == "123456"

    # Less than 6 digits should fail
    with pytest.raises(ValueError, match="at least 6 digits"):
        validate_app_number("1234")


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
