"""Tests del gating de índices por plan (Sentinel-2)."""

from types import SimpleNamespace

from parcels.sentinel2 import ALL_INDICES, _allowed_indices_for_request


def _request(features=None, superuser=False, subscription=True):
    plan = SimpleNamespace(features_included=features or [])
    sub = SimpleNamespace(plan=plan) if subscription else None
    user = SimpleNamespace(is_superuser=superuser)
    return SimpleNamespace(user=user, subscription=sub)


def test_free_solo_ndvi():
    assert _allowed_indices_for_request(_request(['ndvi'])) == ['ndvi']


def test_basic_ndvi_ndmi_savi():
    assert _allowed_indices_for_request(_request(['ndvi', 'ndmi', 'savi'])) == [
        'ndvi', 'ndmi', 'savi'
    ]


def test_pro_todos_los_indices():
    assert _allowed_indices_for_request(
        _request(['ndvi', 'ndmi', 'savi', 'ndre'])
    ) == list(ALL_INDICES)


def test_sin_suscripcion_solo_ndvi():
    req = SimpleNamespace(user=SimpleNamespace(is_superuser=False), subscription=None)
    assert _allowed_indices_for_request(req) == ['ndvi']


def test_superusuario_tiene_todos():
    assert _allowed_indices_for_request(_request(['ndvi'], superuser=True)) == list(ALL_INDICES)
