from app.services.cpe_accounting import _should_auto_validate_cpe


def test_auto_validate_when_clean_and_a_controler() -> None:
    # #7 CPE : aucun contrôle error/blocked + statut encore a_controler -> valide
    assert _should_auto_validate_cpe("a_controler", 0, 0) is True


def test_no_auto_validate_with_error_or_blocked() -> None:
    # un écart (error) OU un point bloquant (blocked) empêche l'auto-validation
    assert _should_auto_validate_cpe("a_controler", 1, 0) is False
    assert _should_auto_validate_cpe("a_controler", 0, 1) is False
    assert _should_auto_validate_cpe("a_controler", 2, 3) is False


def test_never_override_human_decision() -> None:
    # une décision humaine déjà prise n'est jamais écrasée, même si tout est propre
    for human in ("valide", "refuse", "conteste"):
        assert _should_auto_validate_cpe(human, 0, 0) is False
