"""
GuardX — Demo Hardware Domain Intelligence Engine

Hardware-Aligned for Demo Setup:
  ESP32 + MPU6050 + DS18B20 + HX711 + Load Cell + ACS712 + PWM Motor

This module encodes domain knowledge for a DEMO-SCALE motor rig.
Thresholds are calibrated for small motor, NOT industrial CNC.

Fault Signature Mapping (5 fault types):
  bearing_wear, imbalance, overheating, overload, coolant_failure

References:
  - ISO 10816 (Vibration Severity — scaled down for demo motor)
  - General motor diagnostics principles (adapted to demo scale)
"""

import numpy as np
from typing import Optional
from config import DEMO_THRESHOLDS, NORMAL_BASELINES


# ─── Demo Motor Thresholds ─────────────────────────────────────
# These are calibrated for a small DC/BLDC motor, NOT a real CNC spindle.
T = DEMO_THRESHOLDS


# ─── Fault Signature Mapper (Demo Hardware) ────────────────────
def diagnose_cnc_fault(
    vibration_rms: float,
    temperature: float,
    temperature_rate: float = 0.0,
    cutting_force: float = 0.0,
    force_variance: float = 0.0,
    motor_current: float = 0.0,
    speed_command_level: float = 65.0,
) -> dict:
    """
    Rule-based fault signature mapping for demo hardware.

    This is DOMAIN INTELLIGENCE — it encodes what a maintenance engineer
    knows, translated into programmatic rules calibrated for demo motor.

    Signature Matrix (Demo Hardware):
    ┌─────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
    │ Fault Mode          │ Vib RMS  │ Temp     │ TempRate │ Force    │ Current  │
    ├─────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
    │ Bearing Wear        │ RISING   │ RISING   │ SLIGHT   │ RISING   │ SLIGHT   │
    │ Imbalance           │ OSCILLAT │ NORMAL   │ NORMAL   │ OSCILLAT │ SLIGHT   │
    │ Overheating         │ SLIGHT   │ HIGH     │ HIGH     │ SLIGHT   │ SLIGHT   │
    │ Overload            │ HIGH     │ RISING   │ MODERATE │ VERY HI  │ HIGH     │
    │ Coolant Failure     │ SLIGHT   │ HIGH     │ VERY HI  │ SLIGHT   │ NORMAL   │
    │ Normal Operation    │ LOW      │ NORMAL   │ ~0       │ NORMAL   │ NORMAL   │
    └─────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

    Args:
        vibration_rms: Vibration RMS in g (MPU6050)
        temperature: Temperature in °C (DS18B20)
        temperature_rate: Rate of temperature change in °C/s (derived)
        cutting_force: Force in N (HX711 + Load Cell)
        force_variance: Rolling variance of force in N² (derived)
        motor_current: Current in A (ACS712)
        speed_command_level: PWM duty cycle % (ESP32)

    Returns:
        Dict with diagnosed fault, confidence, and evidence.
    """
    b = NORMAL_BASELINES
    scores = {}
    evidence = {}

    # ── BEARING WEAR ──
    # Signature: Gradual vibration RMS increase + force increase + current creep
    bearing_score = 0
    brg_evidence = []
    if vibration_rms > T["vibration_rms"]["warning"]:
        bearing_score += 30
        brg_evidence.append(f"Vibration RMS={vibration_rms:.4f}g (above {T['vibration_rms']['warning']}g warning)")
    if vibration_rms > T["vibration_rms"]["critical"]:
        bearing_score += 15
        brg_evidence.append(f"CRITICAL: Vibration RMS={vibration_rms:.4f}g exceeds {T['vibration_rms']['critical']}g")
    if cutting_force > T["cutting_force"]["warning"]:
        bearing_score += 20
        brg_evidence.append(f"Force={cutting_force:.1f}N (bearing friction adding resistance)")
    if motor_current > T["motor_current"]["warning"]:
        bearing_score += 15
        brg_evidence.append(f"Current={motor_current:.3f}A (motor straining)")
    if temperature_rate > 0.1 and temperature_rate < 0.5:
        bearing_score += 10
        brg_evidence.append(f"Slight temp rise rate={temperature_rate:.3f}°C/s (friction heating)")
    # Anti-signal: if temp is rising very fast, it's more likely overheating/coolant
    if temperature_rate > 0.5:
        bearing_score -= 10
    scores["bearing_wear"] = max(0, min(100, bearing_score))
    evidence["bearing_wear"] = brg_evidence

    # ── IMBALANCE ──
    # Signature: Periodic vibration oscillation + high force variance + normal temp
    imbalance_score = 0
    imb_evidence = []
    if force_variance > 5.0:
        imbalance_score += 30
        imb_evidence.append(f"Force variance={force_variance:.2f}N² (oscillation detected)")
    if vibration_rms > b["vibration_rms"]["mean"] + 3 * b["vibration_rms"]["std"]:
        imbalance_score += 25
        imb_evidence.append(f"Vibration RMS={vibration_rms:.4f}g (3σ above normal)")
    if temperature < T["temperature"]["warning"]:
        imbalance_score += 15
        imb_evidence.append("Temperature normal — rules out thermal causes")
    if abs(temperature_rate) < 0.1:
        imbalance_score += 10
        imb_evidence.append("Stable temperature rate confirms mechanical, not thermal fault")
    scores["imbalance"] = min(100, imbalance_score)
    evidence["imbalance"] = imb_evidence

    # ── OVERHEATING ──
    # Signature: High temperature + elevated temp rate + slight force increase
    overheat_score = 0
    oht_evidence = []
    if temperature > T["temperature"]["warning"]:
        overheat_score += 30
        oht_evidence.append(f"Temperature={temperature:.1f}°C (above {T['temperature']['warning']}°C warning)")
    if temperature > T["temperature"]["critical"]:
        overheat_score += 20
        oht_evidence.append(f"CRITICAL: {temperature:.1f}°C exceeds {T['temperature']['critical']}°C shutdown")
    if temperature_rate > 0.2:
        overheat_score += 20
        oht_evidence.append(f"Temp rate=+{temperature_rate:.3f}°C/s (active heating)")
    if vibration_rms < T["vibration_rms"]["warning"]:
        overheat_score += 15
        oht_evidence.append("Low vibration confirms thermal, not mechanical fault")
    # Anti-signal: if temp rate is extremely high, more likely coolant failure
    if temperature_rate > 0.8:
        overheat_score -= 15
    scores["overheating"] = max(0, min(100, overheat_score))
    evidence["overheating"] = oht_evidence

    # ── OVERLOAD ──
    # Signature: High force + high current + vibration increase + temp rising
    overload_score = 0
    ovl_evidence = []
    if cutting_force > T["cutting_force"]["critical"]:
        overload_score += 35
        ovl_evidence.append(f"Force={cutting_force:.1f}N (exceeds {T['cutting_force']['critical']}N critical)")
    elif cutting_force > T["cutting_force"]["warning"]:
        overload_score += 20
        ovl_evidence.append(f"Force={cutting_force:.1f}N (above {T['cutting_force']['warning']}N warning)")
    if motor_current > T["motor_current"]["critical"]:
        overload_score += 30
        ovl_evidence.append(f"Current={motor_current:.3f}A (motor stall risk at {T['motor_current']['critical']}A)")
    elif motor_current > T["motor_current"]["warning"]:
        overload_score += 20
        ovl_evidence.append(f"Current={motor_current:.3f}A (above {T['motor_current']['warning']}A warning)")
    if vibration_rms > T["vibration_rms"]["warning"]:
        overload_score += 15
        ovl_evidence.append(f"Vibration RMS={vibration_rms:.4f}g (mechanical stress from overload)")
    scores["overload"] = min(100, overload_score)
    evidence["overload"] = ovl_evidence

    # ── COOLANT FAILURE ──
    # Signature: Very fast temperature rise (faster than regular overheating)
    coolant_score = 0
    clt_evidence = []
    if temperature_rate > 0.5:
        coolant_score += 35
        clt_evidence.append(f"Temp rate=+{temperature_rate:.3f}°C/s (abnormally fast — coolant may be offline)")
    if temperature_rate > 1.0:
        coolant_score += 20
        clt_evidence.append(f"CRITICAL: Temp rate=+{temperature_rate:.3f}°C/s (confirmed rapid heating)")
    if temperature > T["temperature"]["warning"]:
        coolant_score += 20
        clt_evidence.append(f"Temperature={temperature:.1f}°C (above warning threshold)")
    if vibration_rms < T["vibration_rms"]["warning"]:
        coolant_score += 10
        clt_evidence.append("Low vibration — not a mechanical fault")
    if motor_current < T["motor_current"]["warning"]:
        coolant_score += 10
        clt_evidence.append("Normal current — motor itself is fine, cooling system suspect")
    scores["coolant_failure"] = min(100, coolant_score)
    evidence["coolant_failure"] = clt_evidence

    # ── DETERMINE PRIMARY DIAGNOSIS ──
    primary_fault = max(scores, key=scores.get)
    primary_confidence = scores[primary_fault]

    # If no fault scores above 25%, machine is normal
    if primary_confidence < 25:
        primary_fault = "normal"
        primary_confidence = 100 - max(scores.values()) if scores else 100
        evidence["normal"] = ["All sensor signatures within demo motor operating envelope"]

    return {
        "primary_diagnosis": primary_fault,
        "confidence": primary_confidence,
        "evidence": evidence.get(primary_fault, []),
        "all_scores": scores,
        "thresholds_used": {
            "vibration_rms": T["vibration_rms"],
            "temperature": T["temperature"],
            "cutting_force": T["cutting_force"],
            "motor_current": T["motor_current"],
        },
    }
