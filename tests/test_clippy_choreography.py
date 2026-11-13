from clippy_all_catalog import catalog
from clippy_choreography import study, validate_studies


def test_studies_cover_real_source_frames_without_gaps():
    validate_studies(catalog())


def test_major_actions_require_prop_choreography():
    assert [s[:2] for s in study("SendMail")] == [
        (0, 3),
        (4, 7),
        (8, 12),
        (13, 18),
        (19, 23),
        (24, 48),
        (49, 53),
        (54, 62),
    ]
    assert study("Save")[-1][:2] == (40, 41)
    assert study("Idle1_1")[-2][:2] == (37, 41)
    assert catalog()["Idle1_1"]["frames"][39]["duration"] == 900
    assert all(study(name) is not None for name in catalog())
