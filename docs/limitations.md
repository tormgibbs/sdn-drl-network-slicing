# Known Limitations — DRL Agent and Heuristic Baseline

This document tracks known, understood limitations of the DRL agent (`models/selected/magnolia.zip`)
and the rule-based heuristic baseline (`agent/heuristic_runner.py`). These are behavioral/design
characteristics, not infrastructure bugs — see `docs/known-issues.md` for infrastructure and
measurement-tooling caveats.

## DRL Agent

- **vle → student_portal allocation bias.** The trained policy consistently under-serves
  `student_portal` relative to `vle` by a small margin, confirmed via `eval/03`'s reward-delta
  sweep (win_rate ~70-75% at small delta, decaying to ~22% by delta=0.20). Traced to the reward
  function's SLA-threshold asymmetry (`student_portal.max_latency_ms=50` vs `vle.max_latency_ms=100`),
  which makes the same physical latency contribute a larger penalty for `student_portal`. Reproduced
  independently across two separately-trained checkpoints (`laurel`, `linden`), indicating it is a
  structural property of the reward landscape, not undertraining. Non-blocking for promotion:
  `student_portal` was not observed near its SLA boundary during this bias's manifestation. See
  decision log 014's follow-up for full analysis.
- **Limited live-network validation.** Only one `infer.py` run has been performed against the real
  testbed (50 steps, ~100 seconds), showing generally healthy reward with one real, well-attributed
  SLA-violation event (a genuine 273ms latency spike on `vle`, confirmed via direct log
  cross-reference, not a measurement artifact). This is a short window; longer-duration validation
  has not yet been performed.
- **No controlled baseline comparison yet.** The agent's performance has not yet been measured
  side-by-side against the static or heuristic baselines under matched traffic conditions.

- **IoT under-allocation is structural, not undertraining.** Reward-delta analysis
  (`eval/03_reward_delta_grid.py`) shows the policy leaves reward on the table on `iot`:
  taking bandwidth away from it never improves reward (0-3.1% win rate across all four
  counter slices), while giving it more always does (100% win rate, even from the
  lowest-priority `general` slice). Reproduced across two independently-trained
  checkpoints (`magnolia`, `maple`, 504K timesteps each) with near-identical numbers,
  which argues for a converged equilibrium, not incomplete training.

  Likely cause: `iot`'s floor (64 kbps) is under 1% of total capacity, and softmax
  struggles to express such a small target fraction precisely. The step-size sweep
  shows a high clip rate (19.6% at delta=0.01, 100% by delta=0.05) when constructing
  "give iot more" counter-allocations, consistent with a narrow, easy-to-overshoot
  target region.

  Not tested: whether more training changes this. A fix, if pursued, would likely need
  a reward-weight or action-space change rather than longer training.

## Heuristic Baseline

- **No hysteresis.** The rule re-evaluates every step from scratch with no memory of why a slice's
  allocation is currently elevated. A slice's gains from a prior trigger can be partially clawed
  back on the very next step if a different slice crosses the utilisation threshold, since the bump
  is taken proportionally from whichever slices are not currently triggered at that instant. This
  is a real behavioral difference from the DRL agent, which exhibits more stable, priority-aware
  allocation via its fairness/oscillation reward terms.
- **Fixed, unvalidated threshold and step size.** `_UTIL_THRESHOLD = 0.80` and `_STEP_SIZE = 0.05`
  are set to match the thesis's illustrative example, not empirically tuned or justified against
  the actual traffic model.
- **Limited test coverage.** Validated over ~100 steps under one traffic condition (sustained `vle`
  demand). Not yet tested across the full scenario set (`registration`, `quiz`, `chaos`, etc.)
  the way the DRL agent was via the sim-side eval scripts.