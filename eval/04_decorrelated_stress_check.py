"""
Filter real 'chaos' scenario episodes for a specific decorrelated stress
combination (e.g. "slice A stressed, slice B NOT stressed"), and check what
the policy actually does in those genuine, in-distribution states.

WHY THIS EXISTS:
If two slices are only ever stressed together in your scenario set (e.g.
'registration' stresses both student_portal AND admin every time), a
policy trained on that data will correctly learn "these move together" --
which then looks like a bug on a hand-built probe that decorrelates them,
even though it's actually a training-data confound, not a policy defect.
'chaos' scenarios sample each slice's factor independently, so they're the
right place to look for genuine decorrelated in-distribution examples.

Always check this BEFORE concluding a policy has a "bias" toward one slice
over another based on scenarios where they're always co-stressed.

USAGE:
    uv run python 04_decorrelated_stress_check.py

Edit SLICE_A / SLICE_B and the factor thresholds below.
"""

import numpy as np
import yaml
from stable_baselines3 import PPO

from agent.sim_env import SimCampusEnv

SLICES_CONFIG_PATH = "config/slices.yaml"
MODEL_PATH = "models/hawthorn/final"
N_EPISODES = 500

SLICE_A = "student_portal"   # the slice you want stressed
SLICE_A_MIN_FACTOR = 1.1
SLICE_B = "admin"            # the slice you want NOT stressed
SLICE_B_MAX_FACTOR = 0.7


def main() -> None:
    slices_cfg = yaml.safe_load(open(SLICES_CONFIG_PATH))
    slice_order = slices_cfg["slice_order"]
    env = SimCampusEnv(slices_cfg)
    model = PPO.load(MODEL_PATH)

    found = 0
    for _ in range(N_EPISODES):
        obs, _ = env.reset()
        if env._scenario != "chaos":
            continue
        a_factor = env._factors[SLICE_A]
        b_factor = env._factors[SLICE_B]
        if not (a_factor > SLICE_A_MIN_FACTOR and b_factor < SLICE_B_MAX_FACTOR):
            continue

        action, _ = model.predict(obs, deterministic=True)
        exp = np.exp(action)
        fracs = exp / exp.sum()
        alloc_str = "  ".join(f"{name}={fracs[i]:.3f}" for i, name in enumerate(slice_order))
        print(f"{SLICE_A}_factor={a_factor:.2f} {SLICE_B}_factor={b_factor:.2f} -> {alloc_str}")
        found += 1

    print(f"\n{found} matching episodes out of {N_EPISODES} "
          f"({SLICE_A} stressed >{SLICE_A_MIN_FACTOR}, {SLICE_B} light <{SLICE_B_MAX_FACTOR})")
    if found < 20:
        print("Few matches -- consider raising N_EPISODES for a more reliable read.")


if __name__ == "__main__":
    main()
