"""
Compare PPO checkpoints via real multi-episode rollouts through SimCampusEnv,
using a shared seed sequence so every checkpoint is scored against the exact
same episodes (paired comparison -> much lower variance than independent
random rollouts per checkpoint).

WHY THIS EXISTS:
Hand-crafted synthetic observation vectors (e.g. "SP only stressed":
[0.1, 0.0, 0.2, 0.9, 0.6, 1.0, ...]) are NOT a reliable way to compare
checkpoints. This project measured directly that such synthetic states
occur in ~0.5% of real rollout steps -- comparing checkpoints on them
produced a checkpoint ranking that was later falsified by this real-rollout
method (mean rewards across "800k...final" turned out statistically
indistinguishable, contradicting a synthetic-probe-based "960k is clearly
best, degrades after" conclusion).

Always prefer this method over synthetic probes when picking a checkpoint.

USAGE:
    uv run python 01_checkpoint_comparison.py

Edit CHECKPOINTS and N_EPISODES below as needed.
"""

import numpy as np
import yaml
from stable_baselines3 import PPO

from agent.sim_env import SimCampusEnv

SLICES_CONFIG_PATH = "config/slices.yaml"
MODELS_ROOT = "models/hawthorn"

CHECKPOINTS = [
    "ppo_slicing_800000",
    "ppo_slicing_880000",
    "ppo_slicing_960000",
    "ppo_slicing_1040000",
    "ppo_slicing_1120000",
    "final",
]

N_EPISODES = 1000  # increase for tighter SEM if checkpoints are close


def run_checkpoint(model_path: str, slices_cfg: dict, seeds: list[int]) -> np.ndarray:
    model = PPO.load(model_path)
    env = SimCampusEnv(slices_cfg)
    episode_rewards = []
    for seed in seeds:
        obs, _ = env.reset(seed=seed)
        total = 0.0
        for _ in range(env.episode_length):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            total += reward
            if terminated or truncated:
                break
        episode_rewards.append(total)
    return np.array(episode_rewards)


def main() -> None:
    slices_cfg = yaml.safe_load(open(SLICES_CONFIG_PATH))
    seeds = list(range(N_EPISODES))

    results = {}
    for ckpt in CHECKPOINTS:
        try:
            r = run_checkpoint(f"{MODELS_ROOT}/{ckpt}", slices_cfg, seeds)
            results[ckpt] = r
        except Exception as e:
            print(f"{ckpt:<25} FAILED: {e}")

    print(f"\n=== Unpaired stats (n={N_EPISODES} episodes each) ===")
    for ckpt, r in results.items():
        sem = r.std() / np.sqrt(len(r))
        print(f"{ckpt:<25} mean={r.mean():.3f} std={r.std():.3f} SEM={sem:.3f}")

    # Paired comparison against the first checkpoint -- much lower variance,
    # since scenario-sampling noise cancels out (same seeds -> same episodes).
    baseline_name = CHECKPOINTS[0]
    if baseline_name in results:
        baseline = results[baseline_name]
        print(f"\n=== Paired diff vs {baseline_name} ===")
        for ckpt, r in results.items():
            diff = r - baseline
            se = diff.std(ddof=1) / np.sqrt(len(diff))
            print(
                f"{ckpt:<25} mean_diff={diff.mean():+.4f} paired_SE={se:.4f} "
                f"({'significant' if abs(diff.mean()) > 2 * se else 'not significant'} at ~2SE)"
            )


if __name__ == "__main__":
    main()
