"""Validasi dan normalisasi nilai tonase untuk seluruh importer PEMS."""

from decimal import Decimal, InvalidOperation

TON_QUANTUM = Decimal("0.0001")
FLOAT_TOLERANCE = Decimal("0.0000000001")
MAX_TON_AMOUNT = Decimal("9999999999.9999")


def validate_ton_amount(value):
    """
    Validasi tonase sesuai batas kolom PostgreSQL NUMERIC(14,4).

    Toleransi kecil hanya diterapkan pada float untuk mengatasi
    artefak representasi biner dari Excel.

    Mengembalikan Decimal dengan empat angka desimal atau ValueError.
    """
    try:
        raw_amount = Decimal(str(value))

        if not raw_amount.is_finite() or raw_amount < 0:
            raise ValueError("nilai harus finite dan tidak negatif")

        if raw_amount > MAX_TON_AMOUNT:
            raise ValueError("nilai tonase melebihi batas NUMERIC(14,4)")

        amount = raw_amount.quantize(TON_QUANTUM)

        if amount > MAX_TON_AMOUNT:
            raise ValueError("nilai tonase melebihi batas NUMERIC(14,4)")

        if isinstance(value, float):
            if abs(raw_amount - amount) > FLOAT_TOLERANCE:
                raise ValueError("presisi melebihi 4 angka desimal")
        elif raw_amount != amount:
            raise ValueError("presisi melebihi 4 angka desimal")

        return amount

    except InvalidOperation as exc:
        raise ValueError("nilai tonase tidak valid") from exc
