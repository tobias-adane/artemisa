import pytest

from artemisa_models import AlertLevel, ActionLevel, Classification, resolve_action_level


def test_normal_is_always_nivel_1():
    assert resolve_action_level(Classification.NORMAL, 0.0) == (AlertLevel.NIVEL_1, ActionLevel.INFORMAR)
    assert resolve_action_level(Classification.NORMAL, 1.0) == (AlertLevel.NIVEL_1, ActionLevel.INFORMAR)


def test_attention_below_threshold_is_nivel_2():
    assert resolve_action_level(Classification.ATTENTION, 0.69) == (AlertLevel.NIVEL_2, ActionLevel.ALERTAR)


def test_attention_at_or_above_threshold_is_nivel_3():
    assert resolve_action_level(Classification.ATTENTION, 0.7) == (AlertLevel.NIVEL_3, ActionLevel.CONTACTAR)
    assert resolve_action_level(Classification.ATTENTION, 0.95) == (AlertLevel.NIVEL_3, ActionLevel.CONTACTAR)


def test_emergency_confirmed_is_nivel_4():
    assert resolve_action_level(Classification.EMERGENCY, 0.9, severity_high=True) == (AlertLevel.NIVEL_4, ActionLevel.EMERGENCIA)


def test_emergency_degraded_falls_back_to_nivel_3():
    assert resolve_action_level(Classification.EMERGENCY, 0.9, severity_high=False) == (AlertLevel.NIVEL_3, ActionLevel.CONTACTAR)


def test_golden_rule_never_nivel_4_without_explicit_severity_high_true():
    """
    ARTEMISA_01_PRODUCTO.md #5: nunca ejecutar un Nivel 4 con evidencia
    de Nivel 2 — ningún classification/severity_score por sí solo, sin
    severity_high explícitamente True, puede producir NIVEL_4.
    """
    for classification in Classification:
        for severity_score in (0.0, 0.3, 0.5, 0.7, 0.9, 1.0):
            alert_level, _ = resolve_action_level(classification, severity_score)  # severity_high por default None
            assert alert_level != AlertLevel.NIVEL_4
            alert_level_false, _ = resolve_action_level(classification, severity_score, severity_high=False)
            assert alert_level_false != AlertLevel.NIVEL_4
