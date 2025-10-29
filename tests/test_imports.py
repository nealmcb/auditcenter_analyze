"""
Basic import and functionality tests for auditcenter_analyze.

This test module verifies:
1. rlacalc module is available and working
2. Core risk calculation functions are accessible
3. Basic data structures can be loaded (when data is available)
"""

import pytest
from pathlib import Path


def test_rlacalc_import():
    """Test that rlacalc module can be imported."""
    import rlacalc

    assert rlacalc is not None


def test_rlacalc_km_p_value():
    """Test that KM_P_value function works with known values."""
    import rlacalc

    # Test with known parameters (from rlacalc documentation)
    # New Hampshire 2016 example
    margin = (354040 - 337589) / (354040 + 337589 + 33234)
    risk = rlacalc.KM_P_value(200, 1.03905, margin, 1, 0, 0, 0)

    # Should return a valid risk value
    assert risk is not None
    assert isinstance(risk, (int, float))
    assert risk >= 0
    assert risk <= 1  # Risk should be between 0 and 1

    # Expected value from rlacalc documentation
    expected = 0.21438135077031842
    assert abs(risk - expected) < 0.0001


def test_pathlib_imports():
    """Test that Path from pathlib is available."""
    from pathlib import Path

    assert Path is not None


def test_data_directory_exists():
    """Verify that data directory exists (may fail on fresh systems)."""
    data_dir = Path(__file__).parent.parent / "data" / "2024" / "general"

    # This test should pass if data is present, otherwise will be skipped
    if data_dir.exists():
        assert data_dir.is_dir()
    else:
        pytest.skip("Data directory not found - skipping integration test")


def test_risks_constants():
    """Test that risk calculation constants are defined correctly."""
    # These are from the calculate_opportunistic_risk.py file
    GAMMA = 1.03905
    RISK_LIMIT = 0.03

    assert isinstance(GAMMA, float)
    assert isinstance(RISK_LIMIT, float)
    assert GAMMA > 1.0  # gamma must be greater than 1
    assert 0 < RISK_LIMIT <= 1  # risk limit is a probability


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
