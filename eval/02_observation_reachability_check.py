"""
Check whether a hand-crafted synthetic observation vector is actually
reachable under real rollouts, before trusting any eval/probe built on it.

WHY THIS EXISTS:
A synthetic "SP only stressed" probe made a checkpoint look wrong on one
dimension. This script proved that exact combination of (latency, loss,
utilisation) for a slice occurs in ~0.5% of real steps -- meaning the
checkpoint's behaviour there was almost entirely unconstrained by training
and not a fair test. Run this BEFORE trusting any hand-built observation
probe for checkpoint comparison or behaviour analysis.

USAGE:
    uv run python 02_observation_reachability_check.py

Edit SLICE_INDEX and the synthetic thresholds below to match whatever
probe you're trying to validate.
"""

import numpy as np
import yaml

from agent.sim_env import SimCampusEnv

SLICES_CONFIG_PATH = "config/slices.yaml"
N_EPISODES = 500
STEPS_PER_EPISODE = 20  # sample early-mid episode, not just reset() state

# Which slice's observation triple (latency_i, loss_i, util_i) to check,
# and the synthetic thresholds you want to validate reachability for.
SLICE_INDEX = 0  # 0=vle, 1=student_portal, 2=admin, 3=iot, 4=general per slice_order
LATENCY_THRESHOLD = 0.15   # e.g. "latency_i < 0.15"
LOSS_EXACT = 0.0           # e.g. "loss_i == 0.0"
UTIL_THRESHOLD = 0.25      # e.g. "util_i < 0.25"


def main() -> None:
    slices_cfg = yaml.safe_load(open(SLICES_CONFIG_PATH))
    env = SimCampusEnv(slices_cfg)

    samples = []
    for _ in range(N_EPISODES):
        obs, _ = env.reset()
        for _ in range(STEPS_PER_EPISODE):
            action = env.action_space.sample()
            obs, _, terminated, truncated, _ = env.step(action)
            start = SLICE_INDEX * 3
            samples.append(obs[start:start + 3].tolist())
            if terminated or truncated:
                break

    arr = np.array(samples)
    lat, loss, util = arr[:, 0], arr[:, 1], arr[:, 2]

    print(f"Observation range over {N_EPISODES} episodes x up to {STEPS_PER_EPISODE} steps "
          f"(slice index {SLICE_INDEX}):")
    print(f"  latency_i: min={lat.min():.3f} max={lat.max():.3f} mean={lat.mean():.3f}")
    print(f"  loss_i:    min={loss.min():.3f} max={loss.max():.3f} mean={loss.mean():.3f}")
    print(f"  util_i:    min={util.min():.3f} max={util.max():.3f} mean={util.mean():.3f}")

    print(f"\nFraction matching latency_i < {LATENCY_THRESHOLD}: {(lat < LATENCY_THRESHOLD).mean():.3f}")
    print(f"Fraction matching loss_i == {LOSS_EXACT}:          {(loss == LOSS_EXACT).mean():.3f}")
    print(f"Fraction matching util_i < {UTIL_THRESHOLD}:        {(util < UTIL_THRESHOLD).mean():.3f}")

    all_match = (lat < LATENCY_THRESHOLD) & (loss == LOSS_EXACT) & (util < UTIL_THRESHOLD)
    print(f"\nFraction matching ALL THREE synthetic conditions: {all_match.mean():.4f}")
    print("(If this is near 0, the synthetic probe is out-of-distribution --")
    print(" don't trust checkpoint behaviour on it as representative.)")


if __name__ == "__main__":
    main()
