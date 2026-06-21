from typing import Optional
"""
GuardX — Hardware-Aligned CNC Data Simulator

Generates realistic synthetic sensor data matching actual demo hardware:
  ESP32 + MPU6050 + DS18B20 + HX711 + Load Cell + ACS712 + PWM Motor

Output CSV columns (STRICT ORDER — must match get_feature_vector_columns):
  timestamp, vibration_rms, temperature, temperature_rate, cutting_force,
  force_variance, motor_current, speed_command_level, machine_state, fault_type

Feature Symmetry Contract:
  - temperature_rate = diff of temperature (first value = 0)
  - force_variance = rolling variance of cutting_force (window = ROLLING_WINDOW, first values = 0)
  - ROLLING_WINDOW and NaN handling MUST match services/preprocessing.py exactly

Fault Types (5):
  bearing_wear, imbalance, overheating, overload, coolant_failure
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    NORMAL_BASELINES, SENSOR_RANGES, SIMULATOR_DEFAULT_ROWS,
    ROLLING_WINDOW, SIMULATOR_SAMPLE_RATE,
)

# ─── Constants ───────────────────────────────────────────────────
# Feature column order — MUST match get_feature_vector_columns() in preprocessing.py
FEATURE_ORDER = [
    "vibration_rms", "temperature", "temperature_rate",
    "cutting_force", "force_variance", "motor_current",
    "speed_command_level",
]

CSV_COLUMNS = [
    "timestamp", "vibration_rms", "temperature", "temperature_rate",
    "cutting_force", "force_variance", "motor_current",
    "speed_command_level", "machine_state", "fault_type",
]


# ─── AR(1) Noise (Realistic Signal Drift) ────────────────────────

def _autocorrelated_noise(
    n: int, mean: float, std: float, autocorr: float, rng: np.random.Generator
) -> np.ndarray:
    """Generate autocorrelated noise (AR(1) process) for realistic signal drift."""
    noise = np.zeros(n)
    noise[0] = mean
    for i in range(1, n):
        noise[i] = autocorr * noise[i - 1] + (1 - autocorr) * mean + rng.normal(0, std)
    return noise


# ─── Derived Feature Computation ─────────────────────────────────
# CRITICAL: These functions are the CANONICAL source of truth.
# preprocessing.py MUST use identical logic for live data.

def _compute_temperature_rate(temperature: np.ndarray) -> np.ndarray:
    """Compute temperature rate of change (°C/s). First value = 0."""
    rate = np.diff(temperature, prepend=temperature[0])
    rate[0] = 0.0  # No diff for first sample — matches .diff().fillna(0)
    return rate


def _compute_force_variance(cutting_force: np.ndarray, window: int = ROLLING_WINDOW) -> np.ndarray:
    """Compute rolling variance of cutting force. First values = 0 (backfilled)."""
    series = pd.Series(cutting_force)
    variance = series.rolling(window=window, min_periods=1).var().fillna(0).values
    return variance


# ─── Fault Generators ────────────────────────────────────────────

def _generate_normal(n: int, rng: np.random.Generator) -> dict:
    """Generate normal demo motor operating data."""
    b = NORMAL_BASELINES

    vibration_rms = _autocorrelated_noise(n, b["vibration_rms"]["mean"], b["vibration_rms"]["std"], 0.85, rng)
    temperature = _autocorrelated_noise(n, b["temperature"]["mean"], b["temperature"]["std"], 0.95, rng)
    cutting_force = _autocorrelated_noise(n, b["cutting_force"]["mean"], b["cutting_force"]["std"], 0.88, rng)
    motor_current = _autocorrelated_noise(n, b["motor_current"]["mean"], b["motor_current"]["std"], 0.90, rng)
    speed_cmd = _autocorrelated_noise(n, b["speed_command_level"]["mean"], b["speed_command_level"]["std"], 0.92, rng)

    # Clip to physical ranges
    vibration_rms = np.clip(vibration_rms, 0.01, SENSOR_RANGES["vibration_rms"]["max"])
    temperature = np.clip(temperature, SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"])
    cutting_force = np.clip(cutting_force, 0.5, SENSOR_RANGES["cutting_force"]["max"])
    motor_current = np.clip(motor_current, 0.1, SENSOR_RANGES["motor_current"]["max"])
    speed_cmd = np.clip(speed_cmd, 20, 100)

    # Derived features (MUST match preprocessing.py logic)
    temperature_rate = _compute_temperature_rate(temperature)
    force_variance = _compute_force_variance(cutting_force)

    return {
        "vibration_rms": vibration_rms,
        "temperature": temperature,
        "temperature_rate": temperature_rate,
        "cutting_force": cutting_force,
        "force_variance": force_variance,
        "motor_current": motor_current,
        "speed_command_level": speed_cmd,
        "machine_state": ["normal"] * n,
        "fault_type": ["none"] * n,
    }


def _generate_bearing_wear(n: int, rng: np.random.Generator) -> dict:
    """
    Bearing wear: gradual vibration RMS increase with periodic spikes.
    Force and current increase slowly as friction rises.
    """
    t = np.linspace(0, 1, n)
    b = NORMAL_BASELINES

    # Vibration RMS ramps from normal to warning+
    vibration_rms = b["vibration_rms"]["mean"] + t * 0.18 + rng.normal(0, 0.015, n)
    spike_idx = rng.choice(n, size=max(1, n // 15), replace=False)
    vibration_rms[spike_idx] += rng.uniform(0.05, 0.12, len(spike_idx))

    # Temperature rises slightly due to bearing friction
    temperature = b["temperature"]["mean"] + t * 8 + rng.normal(0, 1.5, n)

    # Cutting force increases as bearing friction adds load
    cutting_force = b["cutting_force"]["mean"] + t * 6 + rng.normal(0, 0.8, n)

    # Motor current creeps up
    motor_current = b["motor_current"]["mean"] + t * 0.25 + rng.normal(0, 0.03, n)

    # Speed command stays roughly constant (operator doesn't change it)
    speed_cmd = b["speed_command_level"]["mean"] + rng.normal(0, 3.0, n)

    # Clip
    vibration_rms = np.clip(vibration_rms, 0.01, SENSOR_RANGES["vibration_rms"]["max"])
    temperature = np.clip(temperature, SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"])
    cutting_force = np.clip(cutting_force, 0.5, SENSOR_RANGES["cutting_force"]["max"])
    motor_current = np.clip(motor_current, 0.1, SENSOR_RANGES["motor_current"]["max"])
    speed_cmd = np.clip(speed_cmd, 20, 100)

    temperature_rate = _compute_temperature_rate(temperature)
    force_variance = _compute_force_variance(cutting_force)

    return {
        "vibration_rms": vibration_rms,
        "temperature": temperature,
        "temperature_rate": temperature_rate,
        "cutting_force": cutting_force,
        "force_variance": force_variance,
        "motor_current": motor_current,
        "speed_command_level": speed_cmd,
        "machine_state": ["fault"] * n,
        "fault_type": ["bearing_wear"] * n,
    }


def _generate_imbalance(n: int, rng: np.random.Generator) -> dict:
    """
    Imbalance: periodic sinusoidal oscillation in vibration RMS.
    Characteristic: vibration oscillates at motor rotation frequency multiples.
    """
    t = np.linspace(0, 2 * np.pi * 5, n)
    b = NORMAL_BASELINES

    # Vibration oscillates sinusoidally — signature of imbalance
    vibration_rms = b["vibration_rms"]["mean"] + 0.06 * np.abs(np.sin(t * 3)) + 0.04 * np.sin(t * 7)
    vibration_rms += rng.normal(0, 0.012, n)
    # Add occasional bursts
    burst_starts = rng.choice(max(1, n - 30), size=max(1, n // 50), replace=False)
    for bs in burst_starts:
        burst_len = rng.integers(10, 30)
        end = min(bs + burst_len, n)
        vibration_rms[bs:end] += rng.uniform(0.04, 0.10)

    temperature = b["temperature"]["mean"] + rng.normal(0, 2.5, n)
    cutting_force = b["cutting_force"]["mean"] + 2 * np.sin(t * 4) + rng.normal(0, 1.0, n)
    motor_current = b["motor_current"]["mean"] + 0.05 * np.sin(t * 2) + rng.normal(0, 0.03, n)
    speed_cmd = b["speed_command_level"]["mean"] + rng.normal(0, 5.0, n)

    vibration_rms = np.clip(vibration_rms, 0.01, SENSOR_RANGES["vibration_rms"]["max"])
    temperature = np.clip(temperature, SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"])
    cutting_force = np.clip(cutting_force, 0.5, SENSOR_RANGES["cutting_force"]["max"])
    motor_current = np.clip(motor_current, 0.1, SENSOR_RANGES["motor_current"]["max"])
    speed_cmd = np.clip(speed_cmd, 20, 100)

    temperature_rate = _compute_temperature_rate(temperature)
    force_variance = _compute_force_variance(cutting_force)

    return {
        "vibration_rms": vibration_rms,
        "temperature": temperature,
        "temperature_rate": temperature_rate,
        "cutting_force": cutting_force,
        "force_variance": force_variance,
        "motor_current": motor_current,
        "speed_command_level": speed_cmd,
        "machine_state": ["fault"] * n,
        "fault_type": ["imbalance"] * n,
    }


def _generate_overheating(n: int, rng: np.random.Generator) -> dict:
    """
    Overheating: temperature ramps up beyond safe threshold.
    Temperature rate increases. Slight force increase as material resistance rises.
    """
    t = np.linspace(0, 1, n)
    b = NORMAL_BASELINES

    # Temperature ramps sharply (t^1.5 for accelerating rise)
    temperature = b["temperature"]["mean"] + t**1.5 * 30 + rng.normal(0, 1.5, n)

    vibration_rms = b["vibration_rms"]["mean"] + t * 0.04 + rng.normal(0, 0.01, n)
    cutting_force = b["cutting_force"]["mean"] + t * 4 + rng.normal(0, 0.8, n)
    motor_current = b["motor_current"]["mean"] + t * 0.15 + rng.normal(0, 0.03, n)
    speed_cmd = b["speed_command_level"]["mean"] + rng.normal(0, 3.0, n)

    vibration_rms = np.clip(vibration_rms, 0.01, SENSOR_RANGES["vibration_rms"]["max"])
    temperature = np.clip(temperature, SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"])
    cutting_force = np.clip(cutting_force, 0.5, SENSOR_RANGES["cutting_force"]["max"])
    motor_current = np.clip(motor_current, 0.1, SENSOR_RANGES["motor_current"]["max"])
    speed_cmd = np.clip(speed_cmd, 20, 100)

    temperature_rate = _compute_temperature_rate(temperature)
    force_variance = _compute_force_variance(cutting_force)

    return {
        "vibration_rms": vibration_rms,
        "temperature": temperature,
        "temperature_rate": temperature_rate,
        "cutting_force": cutting_force,
        "force_variance": force_variance,
        "motor_current": motor_current,
        "speed_command_level": speed_cmd,
        "machine_state": ["fault"] * n,
        "fault_type": ["overheating"] * n,
    }


def _generate_overload(n: int, rng: np.random.Generator) -> dict:
    """
    Overload: sudden force spikes + current spikes.
    Root cause is excessive load on the motor (e.g., depth of cut too deep).
    """
    t = np.linspace(0, 1, n)
    b = NORMAL_BASELINES

    # Cutting force jumps high with random spikes
    cutting_force = b["cutting_force"]["mean"] + 12 + rng.normal(0, 2.0, n)
    spike_idx = rng.choice(n, size=max(1, n // 10), replace=False)
    cutting_force[spike_idx] += rng.uniform(5, 15, len(spike_idx))

    # Motor current spikes with force
    motor_current = b["motor_current"]["mean"] + 0.6 + rng.normal(0, 0.08, n)
    motor_current[spike_idx] += rng.uniform(0.3, 0.8, len(spike_idx))

    # Vibration increases from mechanical stress
    vibration_rms = b["vibration_rms"]["mean"] + 0.08 + rng.normal(0, 0.02, n)
    vibration_rms += 0.03 * np.sin(np.linspace(0, 10 * np.pi, n))

    temperature = b["temperature"]["mean"] + t * 12 + rng.normal(0, 1.5, n)
    speed_cmd = b["speed_command_level"]["mean"] + rng.normal(0, 3.0, n)

    vibration_rms = np.clip(vibration_rms, 0.01, SENSOR_RANGES["vibration_rms"]["max"])
    temperature = np.clip(temperature, SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"])
    cutting_force = np.clip(cutting_force, 0.5, SENSOR_RANGES["cutting_force"]["max"])
    motor_current = np.clip(motor_current, 0.1, SENSOR_RANGES["motor_current"]["max"])
    speed_cmd = np.clip(speed_cmd, 20, 100)

    temperature_rate = _compute_temperature_rate(temperature)
    force_variance = _compute_force_variance(cutting_force)

    return {
        "vibration_rms": vibration_rms,
        "temperature": temperature,
        "temperature_rate": temperature_rate,
        "cutting_force": cutting_force,
        "force_variance": force_variance,
        "motor_current": motor_current,
        "speed_command_level": speed_cmd,
        "machine_state": ["fault"] * n,
        "fault_type": ["overload"] * n,
    }


def _generate_coolant_failure(n: int, rng: np.random.Generator) -> dict:
    """
    Coolant failure: temperature rises FASTER than normal overheating.
    Distinguishing feature: temperature_rate is significantly elevated.
    Force increases slightly as uncooled material is harder to cut.
    """
    t = np.linspace(0, 1, n)
    b = NORMAL_BASELINES

    # Temperature rises rapidly — steeper than overheating
    temperature = b["temperature"]["mean"] + t * 35 + rng.normal(0, 1.0, n)
    # Add step-jumps to simulate sudden coolant loss events
    jump_idx = rng.choice(max(1, n // 3), size=max(1, n // 25), replace=False)
    for j in jump_idx:
        temperature[j:] += rng.uniform(2, 5)

    vibration_rms = b["vibration_rms"]["mean"] + t * 0.03 + rng.normal(0, 0.01, n)
    cutting_force = b["cutting_force"]["mean"] + t * 5 + rng.normal(0, 1.0, n)
    motor_current = b["motor_current"]["mean"] + t * 0.10 + rng.normal(0, 0.03, n)
    speed_cmd = b["speed_command_level"]["mean"] + rng.normal(0, 3.0, n)

    vibration_rms = np.clip(vibration_rms, 0.01, SENSOR_RANGES["vibration_rms"]["max"])
    temperature = np.clip(temperature, SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"])
    cutting_force = np.clip(cutting_force, 0.5, SENSOR_RANGES["cutting_force"]["max"])
    motor_current = np.clip(motor_current, 0.1, SENSOR_RANGES["motor_current"]["max"])
    speed_cmd = np.clip(speed_cmd, 20, 100)

    temperature_rate = _compute_temperature_rate(temperature)
    force_variance = _compute_force_variance(cutting_force)

    return {
        "vibration_rms": vibration_rms,
        "temperature": temperature,
        "temperature_rate": temperature_rate,
        "cutting_force": cutting_force,
        "force_variance": force_variance,
        "motor_current": motor_current,
        "speed_command_level": speed_cmd,
        "machine_state": ["fault"] * n,
        "fault_type": ["coolant_failure"] * n,
    }


# ─── Main Generator ──────────────────────────────────────────────

FAULT_GENERATORS = {
    "bearing_wear": _generate_bearing_wear,
    "imbalance": _generate_imbalance,
    "overheating": _generate_overheating,
    "overload": _generate_overload,
    "coolant_failure": _generate_coolant_failure,
}


def _interleave_blocks(
    df: pd.DataFrame, rng: np.random.Generator,
    min_block: int = 50, max_block: int = 200
) -> pd.DataFrame:
    """Shuffle rows in blocks to create realistic temporal clustering."""
    n = len(df)
    blocks = []
    i = 0
    while i < n:
        block_size = rng.integers(min_block, max_block + 1)
        blocks.append(df.iloc[i:i + block_size])
        i += block_size
    rng.shuffle(blocks)
    return pd.concat(blocks, ignore_index=True)


def generate_chunk(
    n_rows: int,
    fault_ratio: float = 0.30,
    seed: int = 42,
    start_time: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Generate a single chunk of hardware-aligned CNC simulation data.

    Args:
        n_rows: Number of data points in this chunk
        fault_ratio: Fraction of data that contains faults (default 30%)
        seed: Random seed for reproducibility
        start_time: Start timestamp for this chunk

    Returns:
        DataFrame with columns matching CSV_COLUMNS
    """
    rng = np.random.default_rng(seed)

    n_fault = int(n_rows * fault_ratio)
    n_normal = n_rows - n_fault

    fault_types = list(FAULT_GENERATORS.keys())
    n_per_fault = n_fault // len(fault_types)
    remainder = n_fault - n_per_fault * len(fault_types)

    segments = [_generate_normal(n_normal, rng)]
    for i, ft in enumerate(fault_types):
        count = n_per_fault + (1 if i < remainder else 0)
        if count > 0:
            segments.append(FAULT_GENERATORS[ft](count, rng))

    dfs = [pd.DataFrame(seg) for seg in segments]
    df = pd.concat(dfs, ignore_index=True)
    df = _interleave_blocks(df, rng, min_block=50, max_block=200)

    # Generate timestamps (1-second intervals = SIMULATOR_SAMPLE_RATE)
    if start_time is None:
        start_time = datetime.now() - timedelta(seconds=n_rows)
    df["timestamp"] = [
        (start_time + timedelta(seconds=i * SIMULATOR_SAMPLE_RATE)).isoformat()
        for i in range(len(df))
    ]

    # Round sensor values
    df["vibration_rms"] = df["vibration_rms"].round(4)
    df["temperature"] = df["temperature"].round(2)
    df["temperature_rate"] = df["temperature_rate"].round(4)
    df["cutting_force"] = df["cutting_force"].round(2)
    df["force_variance"] = df["force_variance"].round(4)
    df["motor_current"] = df["motor_current"].round(4)
    df["speed_command_level"] = df["speed_command_level"].round(1)

    # Ensure strict column order
    df = df[CSV_COLUMNS]
    return df


def generate_dataset(
    n_rows: int = SIMULATOR_DEFAULT_ROWS,
    fault_ratio: float = 0.30,
    seed: int = 42,
    chunk_size: int = 100_000,
    filepath: str = "data/cnc_simulation_data.csv",
) -> str:
    """
    Generate complete dataset in chunks, writing to disk incrementally.

    This is the SCALABLE generator — handles 5M to 80M+ rows by writing
    500K-row chunks at a time to avoid memory exhaustion.

    Args:
        n_rows: Total number of rows to generate
        fault_ratio: Fraction of fault data (default 30%)
        seed: Random seed for reproducibility
        chunk_size: Rows per chunk (default 500K)
        filepath: Output CSV path

    Returns:
        Absolute path to the generated file
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    total_written = 0
    chunk_num = 0
    base_time = datetime.now() - timedelta(seconds=n_rows * SIMULATOR_SAMPLE_RATE)

    print(f"[*] GuardX Hardware-Aligned Data Simulator")
    print(f"    Target: {n_rows:,} rows | Fault ratio: {fault_ratio:.0%}")
    print(f"    Chunk size: {chunk_size:,} rows")
    print(f"    Output: {filepath}")
    print(f"    Feature order: {FEATURE_ORDER}")
    print()

    while total_written < n_rows:
        rows_remaining = n_rows - total_written
        current_chunk_size = min(chunk_size, rows_remaining)
        chunk_seed = seed + chunk_num  # Vary seed per chunk for variety

        start_time = base_time + timedelta(seconds=total_written * SIMULATOR_SAMPLE_RATE)
        df = generate_chunk(
            n_rows=current_chunk_size,
            fault_ratio=fault_ratio,
            seed=chunk_seed,
            start_time=start_time,
        )

        # Write: header only on first chunk
        write_header = (chunk_num == 0)
        df.to_csv(filepath, mode='a' if chunk_num > 0 else 'w',
                  index=False, header=write_header)

        total_written += len(df)
        chunk_num += 1

        pct = total_written / n_rows * 100
        print(f"    [+] Chunk {chunk_num}: {len(df):,} rows | "
              f"Total: {total_written:,}/{n_rows:,} ({pct:.1f}%)")

    abs_path = os.path.abspath(filepath)
    file_size = os.path.getsize(abs_path)
    print(f"\n[OK] Generation complete!")
    print(f"     File: {abs_path}")
    print(f"     Size: {file_size / (1024**2):.1f} MB ({file_size / (1024**3):.2f} GB)")
    print(f"     Rows: {total_written:,}")

    return abs_path


# ─── CLI Entry Point ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GuardX Hardware-Aligned Data Simulator")
    parser.add_argument("--rows", type=int, default=SIMULATOR_DEFAULT_ROWS,
                        help=f"Number of rows (default: {SIMULATOR_DEFAULT_ROWS:,})")
    parser.add_argument("--fault-ratio", type=float, default=0.30,
                        help="Fraction of fault data (default: 0.30)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--chunk-size", type=int, default=500_000,
                        help="Rows per chunk (default: 500,000)")
    parser.add_argument("--output", type=str, default="data/cnc_simulation_data.csv",
                        help="Output CSV path")
    args = parser.parse_args()

    # Remove old file if exists (clean start)
    if os.path.exists(args.output):
        os.remove(args.output)
        print(f"[!] Removed old file: {args.output}")

    path = generate_dataset(
        n_rows=args.rows,
        fault_ratio=args.fault_ratio,
        seed=args.seed,
        chunk_size=args.chunk_size,
        filepath=args.output,
    )

    # Print summary from first chunk sample
    print(f"\n[*] Validation Sample (first 1000 rows of generated file):")
    sample = pd.read_csv(path, nrows=1000)
    print(f"    Columns: {list(sample.columns)}")
    print(f"    Machine State Distribution:")
    for state, count in sample["machine_state"].value_counts().items():
        print(f"      {state}: {count:,} ({count/len(sample):.1%})")
    print(f"    Fault Type Distribution:")
    for ft, count in sample["fault_type"].value_counts().items():
        print(f"      {ft}: {count:,} ({count/len(sample):.1%})")
    print(f"    Sensor Statistics:")
    for col in FEATURE_ORDER:
        print(f"      {col}: min={sample[col].min():.4f}, max={sample[col].max():.4f}, "
              f"mean={sample[col].mean():.4f}, std={sample[col].std():.4f}")
