from __future__ import annotations

import math

C_M_S = 299_792_458.0
DEFAULT_CARRIER_HZ = 193.1e12


def carrier_frequency_hz() -> float:
    return DEFAULT_CARRIER_HZ


def wavelength_m(freq_hz: float = DEFAULT_CARRIER_HZ) -> float:
    return C_M_S / freq_hz


def frequency_hz_from_wavelength(wavelength_m: float) -> float:
    return C_M_S / wavelength_m


def meters_to_km(value_m: float) -> float:
    return value_m / 1000.0


def km_to_m(value_km: float) -> float:
    return value_km * 1000.0


def dbm_to_watts(dbm: float) -> float:
    return 10 ** (dbm / 10.0) * 1e-3


def watts_to_dbm(watts: float) -> float:
    return 10.0 * math.log10(watts / 1e-3)


def db_to_linear(db: float) -> float:
    return 10 ** (db / 10.0)


def linear_to_db(linear: float) -> float:
    return 10.0 * math.log10(linear)
