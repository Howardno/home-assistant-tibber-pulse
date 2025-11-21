"""DLMS/TLV decoder for Tibber Pulse (Kaifa) – TLV-first, structure-aware."""
from __future__ import annotations

import struct
import logging
import binascii
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)


def crc16_xmodem(data: bytes) -> int:
    """CRC-16/XMODEM: poly 0x1021, init 0x0000."""
    return binascii.crc_hqx(data, 0x0000)


def unescape_hdlc(data: bytes) -> bytes:
    """
    Standard HDLC unescape:
    0x7D is escape byte, next byte XOR 0x20.
    """
    out = bytearray()
    i = 0
    ln = len(data)
    while i < ln:
        b = data[i]
        if b == 0x7D and i + 1 < ln:
            out.append(data[i + 1] ^ 0x20)
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def _safe_parse_timestamp(value: bytes) -> str | None:
    """
    Kaifa timestamp (octet string len=12 starting with 0x07).
    Format: 07 YY YY MM DD DOW HH MM SS HUN TZ...
    In your payload: 07 e9 0b 15 ...
    """
    try:
        if len(value) != 12 or value[0] != 0x07:
            return None

        year = int.from_bytes(value[1:3], "big")
        month = value[3]
        day = value[4]
        hour = value[6]
        minute = value[7]

        # Guard against desync garbage
        if not (1970 <= year <= 2100):
            return None
        if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        return datetime(year, month, day, hour, minute).isoformat()

    except Exception:
        return None


def parse_tlv(payload: bytes) -> dict[str, Any]:
    """
    Parse Kaifa DLMS data stream.
    Handles:
      0x02 STRUCTURE (count byte)
      0x09 OCTET STRING (length byte)
      0x06 DOUBLE-LONG-UNSIGNED (4 fixed bytes)
      0x10 LONG-UNSIGNED (2 fixed bytes)  [samler bare rått, foreløpig]
      0x0F/0x11 small ints (1 fixed byte) [ignoreres foreløpig]
    """
    result: dict[str, Any] = {}
    u32_values: list[int] = []  # alle 0x06-verdier i rekkefølge

    i = 0
    while i < len(payload):
        tag = payload[i]
        i += 1

        # STRUCTURE: next byte is element count
        if tag == 0x02:
            if i >= len(payload):
                break
            _count = payload[i]
            i += 1
            continue

        # OCTET STRING: length byte follows
        if tag == 0x09:
            if i >= len(payload):
                break
            length = payload[i]
            i += 1
            if i + length > len(payload):
                break
            value = payload[i:i + length]
            i += length

            ts = _safe_parse_timestamp(value)
            if ts:
                result["timestamp"] = ts
            elif length == 7:
                result.setdefault("strings", []).append(value.decode(errors="ignore"))
            elif length == 16:
                result["meter_id"] = value.decode(errors="ignore").strip("\x00")
            elif length == 8:
                result["meter_model"] = value.decode(errors="ignore")
            continue

        # DOUBLE-LONG-UNSIGNED: fixed 4 bytes
        if tag == 0x06:
            if i + 4 > len(payload):
                break
            val = struct.unpack(">I", payload[i:i + 4])[0]
            i += 4
            u32_values.append(val)
            continue

        # LONG-UNSIGNED: fixed 2 bytes (foreløpig bare samle)
        if tag == 0x10:
            if i + 2 > len(payload):
                break
            val = struct.unpack(">H", payload[i:i + 2])[0]
            i += 2
            result.setdefault("u16_values", []).append(val)
            continue

        # Small fixed-length ints we don't use yet
        if tag in (0x0F, 0x11):
            if i >= len(payload):
                break
            i += 1
            continue

        # Unknown tag -> stop to avoid desync
        break

    # ---- Mapping heuristics based on your payload order ----
    # I dine meldinger ser vi typisk:
    #   første u32 ~ aktiv effekt (W)
    #   siste 3 u32 ~ strøm per fase (mA) og spenning per fase (0.1V)
    if u32_values:
        result["active_power_import"] = u32_values[0]

    # Try to interpret tail as currents + voltages if enough values
    if len(u32_values) >= 9:
        tail = u32_values[-9:]

        # currents likely in mA -> A (typisk 3 verdier rundt 3000-15000)
        c1, c2, c3 = tail[3], tail[4], tail[5]
        result["current_l1"] = c1 / 1000.0
        result["current_l2"] = c2 / 1000.0
        result["current_l3"] = c3 / 1000.0

        # voltages likely in 0.1V -> V (typisk ~2300)
        v1, v2, v3 = tail[6], tail[7], tail[8]
        result["voltage_l1"] = v1 / 10.0
        result["voltage_l2"] = v2 / 10.0
        result["voltage_l3"] = v3 / 10.0

    # Find cumulative import if a very large kWh-counter is present
    for v in u32_values:
        if v > 100_000:  # heuristic: counters are large
            result["active_import_total"] = v / 1000.0
            break

    #result["raw_u32_values"] = u32_values  # nyttig for videre tuning i debug

    return result

def decode_tibber_pulse_message(payload: bytes) -> dict[str, Any]:
    """
    Public entrypoint.
    Your MQTT payload contains multiple ~ frames and a big TLV block.
    We locate TLV start and parse from there.
    """
    if not payload:
        return {}

    data = unescape_hdlc(payload)

    # Preferred: locate Kaifa STRUCTURE start (seen in your payload)
    tlv_start = data.find(b"\x02\x0d\x09\x07")
    if tlv_start != -1:
        tlv = data[tlv_start:]
        decoded = parse_tlv(tlv)
        if decoded:
            return decoded

    # Fallback: locate timestamp octet string
    ts_start = data.find(b"\x09\x0c\x07")
    if ts_start != -1:
        tlv = data[ts_start:]
        decoded = parse_tlv(tlv)
        if decoded:
            return decoded

    _LOGGER.debug("No TLV block found in payload (len=%d)", len(payload))
    return {}
