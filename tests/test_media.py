import pytest
from netarchitect.errors import PhysicalDistanceViolationError
from netarchitect.media import select_media


def test_copper_exactly_100m():
    d = select_media(100)
    assert "Cat6a" in d.choice


def test_copper_101m_raises():
    with pytest.raises(PhysicalDistanceViolationError):
        select_media(101, force_copper=True)


def test_boundary_100():
    d = select_media(100)
    assert "Cat6a" in d.choice


def test_boundary_101():
    d = select_media(101)
    assert "OM4" in d.choice


def test_boundary_400():
    d = select_media(400)
    assert "OM4" in d.choice


def test_boundary_401():
    d = select_media(401)
    assert "OS2" in d.choice or "SMF" in d.choice


def test_smf_justification_includes_distance():
    d = select_media(22000)
    assert "22000" in d.justification or "22" in d.justification


def test_optical_budget_in_justification():
    d = select_media(5000)
    assert "dBm" in d.justification or "budget" in d.justification.lower()


def test_er_selected_for_long_distance():
    d = select_media(15000)
    assert "ER" in d.choice or "LR" in d.choice


def test_force_copper_beyond_100m_raises():
    with pytest.raises(PhysicalDistanceViolationError):
        select_media(200, force_copper=True)
