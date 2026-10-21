# Concept Firewall
## Research and Engineering Design Document

**Version:** 1.0 (initial research design)  
**Prepared:** October 20, 2026  
**Project type:** Reproducible machine-learning research and experimental safety monitoring  
**Status:** Proposed. No project-specific experiments have been run or results verified.  
**Base architecture:** [HazyResearch/ncm](https://github.com/HazyResearch/ncm)  
**Companion project:** Anytime NCM  
**Initial benchmark:** NCM hard Sudoku (structural correctness), then translation and summarization (semantic fidelity)

---

## 1. Executive Summary

**Concept Firewall** asks whether a pretrained Next-Concept Modeling (NCM) model's intermediate coarse-to-fine representations contain information that predicts mistakes in its final output, and whether an inexpensive monitor can use that information to improve generation outcomes.

NCM generates a hierarchy of discrete latent codes, from coarse to fine. A tokenizer decoder can reconstruct candidate text or structured output from the cumulative representation at different levels. Concept Firewall will inspect these **intermediate codes, latent reconstructions, optionally hidden states, and partial decoded outputs**, train small failure-risk probes, and test interventions triggered before generation completes.

The project must distinguish three questions:

1. **Prediction:** Can state at level `k` predict whether the final output of the current trajectory will be incorrect?
2. **Recoverability:** Given an intermediate state, how often can alternative continuations still yield a correct result?
3. **Intervention:** Does a live decision to continue, retry, restart, or verify improve correctness at the **same measured computation budget**?

A Sudoku failure detector is **not automatically an AI safety detector**. Sudoku provides a clean, objectively labeled initial test bed for the methodology. Only later work on factual consistency, harmful behavior, or privacy/policy violations could justify stronger AI safety claims.

**North-star research question:**

> Can lightweight probes on NCM's coarse-to-fine concept hierarchy predict eventual errors more accurately and earlier than input-only or partial-output baselines, and can those predictions guide cost-effective recovery?

**Primary first milestone:** Reproduce the upstream hard-Sudoku evaluation, record all 12 partial reconstructions, and establish whether an intermediate-state probe beats simple baselines on held-out puzzle identities.

**Non-negotiable principle:** Do not claim novelty, predictive performance, mitigation benefits, or inference speedups until they are experimentally demonstrated. An unsuccessful probe is a valid research outcome.

---

## 2. Relationship to Anytime NCM

Concept Firewall and Anytime NCM should remain **scientifically separable** even if they share code and experimental runs.

| Dimension | Concept Firewall | Anytime NCM |
|---|---|---|
| Main objective | Predict and prevent eventual errors | Stop refinement when further work is not worthwhile |
| Target estimate | Probability of failure, and optionally recoverability | Expected benefit of further refinement |
| Main actions | Continue, targeted retry, restart, route to verifier, abstain | Stop or continue |
| Key metrics | AUROC, AUPRC, calibration, false alarms, recovery | Quality, cost, wall-clock latency, early exits |
| First task | Hard Sudoku correctness probing | Hard Sudoku early-exit opportunity |
| Shared resources | Model loader, partial decoder, trajectories, labels, timing | Same |

**Recommended architecture:** If Anytime NCM is already implemented, reuse its **versioned read-only trajectory format**, checkpoint loader, validators, and source-pinned upstream NCM dependency. Avoid creating a second inconsistent inference implementation. A common `ncm_research_core` module can be extracted later, once interfaces stabilize. Do not make Concept Firewall's correctness depend on an unfinished Anytime NCM feature.

A future combination could estimate both failure risk and value of computation, then choose to stop, continue, or retry. **That combined controller is out of scope for v1.**

---

## 3. Scientific Background and Prior Art

### 3.1 What NCM actually does

The October 2026 NCM paper introduces a multiscale residual VQ-VAE tokenizer and a transformer that predicts discrete latent codes **one hierarchy level at a time**, with parallel prediction within each level. The tokenizer supports partial reconstructions. The released repository provides Sudoku, translation, summarization, and other generation checkpoints.

For hard Sudoku, the current released configuration uses a **12-level hierarchy**, with per-level code lengths of `1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89` and default generation temperature `0.0`. Record the upstream commit in every run; values can change.

The NCM paper illustrates incorrect/incomplete intermediate Sudoku boards becoming correct with further refinement, and non-monotonic translation quality. That makes intermediate failure prediction nontrivial: a currently incorrect partial output is **not the same label** as an eventually incorrect output.

Relevant primary sources:

- [NCM paper, arXiv:2610.14162](https://arxiv.org/abs/2610.14162)
- [Stanford Hazy Research explanation](https://hazyresearch.stanford.edu/blog/2026-10-12-ncm)
- [Official source code](https://github.com/HazyResearch/ncm)
- [Official hard-Sudoku configuration](https://github.com/HazyResearch/ncm/blob/main/config/eval/sudoku-hard.yaml)

### 3.2 Similar work already exists for other architectures

The general concept of detecting mistakes before an AI finishes generating is **not novel**.

- **Chiu and Liu, ACL SRW 2026:** [Probing Functional Correctness in Diffusion Language Models](https://aclanthology.org/2026.acl-srw.15/) trains linear probes on intermediate denoising states of diffusion language models. The authors report emerging correctness signals and offline efficiency experiments. Their [code](https://github.com/guan404ming/dlm-probing) is a useful methodological baseline.
- **Early latent hallucination detection:** [Real-time hallucination detection and intervention via calibrated hidden-state probes](https://www.sciencedirect.com/science/article/pii/S153204642600105X) reports calibrated monitoring and intervention for autoregressive medical LLMs in 2026. The clinical claims are not transferable to NCM without new experiments.
- **Related diffusion intervention work:** [A2D: Any-Order, Any-Step Safety Alignment](https://proceedings.iclr.cc/paper_files/paper/2026/hash/956e5427549a82a7472e02adc88360e9-Abstract-Conference.html) investigates safety behavior and termination in diffusion language models. Search its exact proceedings entry when writing a paper.
- **Conventional factuality probes:** Work on detecting hallucinations from hidden states predates NCM and must be considered when evaluating the novelty of any probe-based method.

**Gap to test, not assume:** The accessible literature reviewed on October 20, 2026 did not establish this exact set of NCM-specific experiments: per-level correctness signals in its discrete hierarchy, conditional failure probability under fixed prefixes, and budget-matched live interventions. The absence of a verified match is **not proof no such work exists**.

### 3.3 The distinction that matters

A basic project that trains logistic regression on NCM states and predicts errors may be an architecture adaptation, not a strong novel research contribution. The most valuable possible findings would be:

1. NCM-specific **where/when** correctness information appears, independently of simple puzzle difficulty.
2. How much information lives in **discrete codes vs cumulative latents vs transformer hidden states vs decoded text**.
3. Whether a high-risk intermediate state is **recoverable** under alternative completions.
4. Whether a probe-guided intervention improves the quality-compute frontier **against strong, equally expensive retry and verifier baselines**.

---

## 4. Scope and Non-Goals

### MVP, in scope

- Reproduce the released hard-Sudoku baseline.
- Record per-level code hierarchies, partial reconstructions, and candidate outputs without altering the original generator.
- Define exact Sudoku correctness labels and separate *current-level correctness* from *final correctness*.
- Train and evaluate low-complexity supervised probes on frozen NCM representations.
- Compare against input-only, level-only, confidence-only, decoded-output, and random/shuffled baselines.
- Evaluate out-of-sample calibration, failure detection, false-positive rate, and lead levels before completion.
- Quantify the difference between **predicting a single trajectory's outcome** and **estimating risk over alternative future continuations**.
- Produce transparent results, confidence intervals, failures, and a reproducible research report.

### Follow-on phases

- Capture selected transformer activations with controlled hooks.
- Implement resume-from-prefix for probabilistic counterfactual completions.
- Benchmark live interventions at fixed wall-clock and GPU-work budgets.
- Extend to translation and summarization for grounded factuality and semantic correctness.
- Build a visual trajectory explorer once scientific results justify it.

### Explicit non-goals

- Training a new foundation model in v1.
- Claiming discrete codes are human-readable concepts or intentions.
- Calling Sudoku errors harmful-content or policy-safety violations.
- Claiming that a post-hoc offline filtering simulation demonstrates a deployable protection system.
- Fitting to the official test split and simultaneously calling that split an untouched test result.
- Demonstrating harmful prompt-injection techniques, privacy leaks, or attacks against real users.
- Building a consumer chatbot, hosted security API, or frontend before baselines work.

---

## 5. Precise Research Questions and Hypotheses

### RQ1: Early prediction

For each intermediate level `k`, can a probe distinguish trajectories whose **final level K** is incorrect from those whose final output is correct?

- **H1:** At some intermediate `k < K`, a probe using NCM representations achieves held-out AUROC higher than input-only and level-only controls.
- **Null:** Internal representations add no useful incremental signal beyond obvious difficulty or already decoded evidence.

### RQ2: Temporal dynamics

Does predictability increase monotonically across hierarchy levels, or do signals appear, disappear, or reverse?

- **H2:** Prediction performance varies systematically with representation level and representation type.
- **Null:** Most predictive signal comes from puzzle difficulty and does not improve with refinement.

### RQ3: Recoverability / the point of no return

Given an observed prefix of concept codes `z_{1:k}`, what fraction of **stochastically sampled** suffix completions solve the same puzzle?

- **H3:** Some partial states carry strong information about conditional completion success that is not evident from current decoded correctness alone.
- **Important:** This statement is meaningful only after configuring and validating a **non-deterministic** continuation process. The published hard-Sudoku default has temperature `0.0`. Repeating the unchanged deterministic decoder would produce no useful branching distribution.

### RQ4: Actionability

Can acting on risk predictions improve correct completions per unit cost compared with unconditional retries, fixed-level restarts, and cheap deterministic Sudoku validation?

- **H4:** At least one probe-guided policy improves a held-out quality-compute operating point after all monitoring and retry costs are included.
- **Null:** The probe is descriptive only; conventional retries or validation are as good or better.

### RQ5: Transfer (later)

Do failure signals remain useful on factual errors in WMT14 translation and XSum summarization, using an independently evaluated source-faithfulness target?

- **H5:** An NCM-level probe offers predictive value on at least one natural-language task beyond a partial-output checker.
- **Null:** The usefulness is specific to exact-verifiable Sudoku boards.

---

## 6. Formal Definition of Failure Risk

Let `x` be a task input and `Z_{1:k}` the discrete codes generated through level `k` of an NCM model with a total of `K` levels. Let `D(Z_{1:k})` be the decoded partial output, and `Y_K` be the eventual final output from the current generation trajectory.

**Trajectory correctness label:**

`e = 1[Verify(x, Y_K) == false]`

For Sudoku, `Verify` returns true only if the board is well-formed, complete, satisfies every original clue, and satisfies all row/column/subgrid rules. Invalid decoding and malformed boards count as failures.

**Trajectory risk prediction:**

`p_k = Probe(features(x, Z_{1:k})) ≈ P(e=1 | observed state at level k)`

A separate target is required for counterfactual prefixes:

**Conditional prefix risk:**

`r_k = P(Verify(x, Y_K)=false | x, Z_{1:k}, decoding policy)`

`r_k` can be approximated by sampling many valid suffix continuations **from the same fixed prefix** under a specified stochastic generation policy. A single binary result from a deterministic continuation is not a robust estimate of this probability.

**Crucial separation:** A probe predicting `e` from one observed trajectory is not automatically a probe predicting `r_k` over all possible continuations. Treat them as different models/tasks with different supervision and evaluation.

**Lead time:** Levels remaining when the probe first fires, and separately **actual milliseconds/compute remaining**. Level count is not a reliable proxy for time because code lengths and costs vary by level.

---

## 7. Proposed System Architecture

```text
              Frozen official NCM checkpoint
  Input ---> Context encoding / generation level 1..K
                           |
                +----------+-----------+
                |                      |
         Cumulative code hierarchy   Optional hidden-state hooks
                |                      |
      Partial latent reconstruction    Aggregated activations
                |                      |
       Optional partial text/board      |
                +-----------+----------+
                            |
                    LevelState collector
                            |
           +----------------+----------------+
           |                                 |
       Trajectory store                 Feature extraction
           |                                 |
       Gold labels                  Frozen encoder + probe
           |                                 |
           +----------------+----------------+
                            |
              Offline evaluation and calibration
                            |
                    Intervention policy
              [offline first, then live]
                            |
          Measured quality / compute / risk results
```

There are **three physically different execution modes**:

1. **Upstream-equivalent full generation:** No probe and no instrumentation beyond ordinary output. Used to reproduce official results.
2. **Full-depth instrumented trajectory collection:** Generate every level, record states, and compute labels. This can support offline experiments but provides **no real-time stopping savings**.
3. **Live policy-controlled generation:** Requires a narrowly scoped callback/resume hook in the NCM generation loop. Only this mode can demonstrate real compute savings or intervention effects.

Start with (1), then (2). Do not implement (3) until output-equivalence tests pass.

---

## 8. Repository Structure

The project should be a separate Git repository named `concept-firewall`. If a compatible Anytime NCM core already exists, factor the shared code as a dependency only after basic interfaces are tested.

```text
concept-firewall/
├── README.md
├── DESIGN.md                          # this document
├── pyproject.toml
├── requirements.lock                  # generated from working environment
├── .gitignore
├── configs/
│   ├── sudoku_smoke.yaml
│   ├── sudoku_probe.yaml
│   ├── sudoku_branching.yaml
│   ├── intervention.yaml
│   └── wmt14_factuality.yaml
├── third_party/
│   └── ncm/                           # pinned upstream Git submodule
├── src/concept_firewall/
│   ├── upstream_adapter.py            # checkpoint and tokenizer loading
│   ├── level_capture.py               # codes, latents and optional hooks
│   ├── schema.py                      # typed shared trajectory records
│   ├── sudoku_labels.py               # exact, deterministic verifier
│   ├── representations.py             # feature extraction at level k
│   ├── probes.py                      # logistic and small MLP probes
│   ├── training.py                    # group splits and fitting
│   ├── calibration.py                 # temperature/isotonic + thresholds
│   ├── metrics.py                      # discrimination, calibration, FPR
│   ├── counterfactuals.py             # fixed-prefix branching (later)
│   ├── intervention.py                # policy actions and baselines (later)
│   ├── timing.py                      # CUDA synchronization and timing
│   └── cli.py                         # commands added and tested by Codex
├── tests/
│   ├── test_sudoku_labels.py
│   ├── test_partial_reconstruction.py
│   ├── test_baseline_equivalence.py
│   ├── test_no_future_leakage.py
│   ├── test_group_splitting.py
│   ├── test_calibration.py
│   ├── test_counterfactual_prefix.py
│   └── test_intervention_budget.py
├── data/                               # ignored: downloaded datasets
├── artifacts/                          # ignored: upstream weights
├── results/
│   ├── manifests/
│   ├── trajectories/
│   ├── probes/
│   ├── figures/
│   └── reports/
└── docs/
    ├── reproduction_log.md
    ├── experiment_protocol.md
    ├── upstream_compatibility.md
    └── limitations.md
```

Do not commit checkpoint binaries, private datasets, API secrets, massive activation tensors, or an entire vendored copy of the upstream source without an explicit licensing and storage reason. Keep the MIT notice for NCM code and document any local upstream patches.

---

## 9. Development Environment and Setup

### 9.1 Requirements

- Python 3.10+.
- Git, enough disk for selected model/dataset files and collected features.
- PyTorch with CUDA support and a compatible NVIDIA GPU, ideally Linux or Ubuntu via WSL2 on Windows.
- A standard Python environment manager (`venv` is sufficient).
- Hugging Face's `hf` command-line interface.

**Hardware caveat:** No local GPU or model runtime has been benchmarked for this design. The official evaluation workflow assumes CUDA. If using a CPU-only laptop, prioritize unit tests, previously collected feature analysis, or a compatible hosted Linux GPU. Do not represent an unverified CPU patch as official support.

### 9.2 Create the repository

Run in an Ubuntu/WSL2 or Linux terminal:

```bash
mkdir concept-firewall
cd concept-firewall
git init
git submodule add https://github.com/HazyResearch/ncm.git third_party/ncm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Pin and record the upstream submodule SHA **before** collecting any results:

```bash
git -C third_party/ncm rev-parse HEAD
```

Do not automatically track future upstream changes during a reproducibility run.

### 9.3 Install a compatible CUDA PyTorch build

Choose the appropriate installation command from [PyTorch's official installer](https://pytorch.org/get-started/locally/) for the GPU driver and CUDA combination. The exact command varies by hardware, so this document deliberately does not hard-code a CUDA wheel URL.

After installing PyTorch, install NCM's dependencies and experiment packages:

```bash
python -m pip install -r third_party/ncm/requirements.txt
python -m pip install \
  huggingface_hub pandas numpy scipy scikit-learn \
  matplotlib pyarrow pyyaml pytest
python - <<'PY'
import torch
print('torch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
print('torch CUDA runtime:', torch.version.cuda)
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
PY
```

If an upstream dependency changes the PyTorch build, reinstall the compatible CUDA build and confirm `torch.cuda.is_available()` again. Then capture dependency versions in `requirements.lock` or a real resolver-generated lockfile. Never assume `pip freeze` is equivalent to a cross-platform dependency lock.

### 9.4 Download only the Sudoku-hard artifacts

The official README lists whole-repository downloads, but this project should first download only the necessary task files:

```bash
hf download hazyresearch/ncm-checkpoints \
  --include 'sudoku-hard/*' \
  --local-dir artifacts

hf download hazyresearch/ncm-datasets \
  --repo-type dataset \
  --include 'sudoku-hard/*' \
  --local-dir data
```

Check the actual Hub directory structure and current filenames before proceeding. The official evaluator expects a task-level checkpoint directory and a matching task-level data directory. If wildcard filtering yields unexpected results, inspect `hf download ... --dry-run` or the Hub listing and adjust the filter. Do not guess missing filenames or silently download every model.

References: [checkpoints](https://huggingface.co/hazyresearch/ncm-checkpoints), [datasets](https://huggingface.co/datasets/hazyresearch/ncm-datasets), [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli).

### 9.5 Reproduce upstream inference before adding probes

From the official NCM directory:

```bash
cd third_party/ncm
python evaluate.py \
  --config config/eval/sudoku-hard.yaml \
  --checkpoint-dir ../../artifacts/sudoku-hard \
  --data-dir ../../data/sudoku-hard \
  --gpus 0 \
  --n 32 \
  --out ../../results/upstream_smoke
cd ../..
```

This is a **32-input smoke run**, not a statistical evaluation. Verify that the evaluator's CLI accepts these flags at the pinned commit, check both the printed metrics and shard logs, and document exact commands. Run the official larger evaluation separately once the environment works.

Record:

- NCM commit SHA and checkpoint hashes.
- GPU, driver, PyTorch/CUDA versions, Python and package versions.
- Config, seeds, temperature, sampling parameters, batch size, and data revision.
- Upstream solved/valid-grid rates and raw predictions, where available.
- Any deviations needed for smaller GPU memory, explicitly flagged as deviations.

**Exit gate:** No custom probe work until the upstream checkpoint loads and generates valid results.

---

## 10. Verified Upstream Integration Points

The current upstream evaluator is in `scripts/eval_shard.py`. Its final generation path calls the generator and then reconstructs a full hierarchy:

```python
# Illustrative extraction of the upstream interface, not a complete script.
generated_codes = net.generate(
    level0, context,
    temperature=temp,
    top_k=top_k,
    top_p=top_p,
    cfg_scale=cfg,
    cfg_null_eos=EOS,
)
_, z_levels = tk.vqvae.vq.idx_to_zhats(
    generated_codes,
    return_zlevels=True,
)
final_logits = tk.vqvae.decoder(z_levels[-1])
```

Here `generated_codes` is the generated hierarchy, and `z_levels` contains cumulative representations. The current evaluator decodes only `z_levels[-1]`. Concept Firewall will instrument the same pathway to decode or inspect `z_levels[k]`, preserving the upstream tokenizer and token-picking rules.

**Source-of-truth locations:**

- [`scripts/eval_shard.py`](https://github.com/HazyResearch/ncm/blob/main/scripts/eval_shard.py)
- [`models/next_concept.py`](https://github.com/HazyResearch/ncm/blob/main/models/next_concept.py)
- [`config/eval/sudoku-hard.yaml`](https://github.com/HazyResearch/ncm/blob/main/config/eval/sudoku-hard.yaml)

**Do not assume** NCM exposes a public Python callback for intermediate activations, or that `idx_to_zhats` contains generator hidden states. It reconstructs tokenizer latent states from generated codes. Transformer hidden states require targeted instrumentation of the generator, separately documented and validated.

### Capturing representations

Capture, where feasible, these distinct feature families:

1. **Input-only:** Clue count, clue pattern, optional deterministic constraint features. These must not include ground-truth solution information.
2. **Discrete code summaries:** Level IDs, codebook index statistics, code entropy or histograms (dimensionally controlled).
3. **Cumulative tokenizer latent features:** Mean/std/norm, carefully selected pooled embedding vectors for `z_levels[k]`.
4. **Decoded board features:** Number of filled cells, row/column conflicts, clue consistency, malformed tokens. This baseline is permitted to use deterministic validation logic, but not a hidden reference solution.
5. **Generator confidence:** Token/code logits or entropy **only if instrumentation truly exposes them**. Do not approximate them with final probabilities not available at decision time.
6. **Transformer activations (advanced):** Pooled hidden states from selected blocks after confirming tensor shapes and avoiding unnecessary activation retention.

Feature collection at level `k` must not touch `z_levels[k+1:]`, future generated codes, final correctness labels, or information computable only after the run finishes. Data collection can happen offline, but the *per-level feature contract* must be enforceable online.

---

## 11. Data Schema and Label Contracts

Use a versioned and efficient storage format (Parquet for tabular data, optionally compressed tensor files for selected samples). A minimal logical schema:

```python
from dataclasses import dataclass, field

@dataclass
class LevelRecord:
    run_id: str
    puzzle_id: str
    trajectory_id: str
    level: int
    available_feature_version: str
    predicted_board: str | None
    current_valid: bool | None
    features: dict[str, float] = field(default_factory=dict)
    generator_ms_incremental: float | None = None
    monitor_ms_incremental: float | None = None

@dataclass
class TrajectoryOutcome:
    trajectory_id: str
    puzzle_id: str
    final_valid: bool
    configuration_id: str
    seed: int
    checkpoint_sha256: str
    upstream_commit: str
```

These classes are **proposed application types**, not existing NCM APIs.

### Label 1: Current intermediate correctness

`current_valid(k)` means the decoded board *at* level `k` is a complete and valid solution to the input puzzle.

### Label 2: Final trajectory correctness

`final_valid(K)` means the final generated board is valid.

The probe's initial binary label is `not final_valid(K)`, **not** `not current_valid(k)`.

### Label 3: Prefix recoverability (only after stochastic extension)

For a frozen prefix, sample `M` suffix completions under a documented nonzero-temperature policy. The empirical failure rate estimates conditional risk, with uncertainty intervals. Record the exact prefix hash, sampler parameters, `M`, and per-branch seed.

Do not present a Monte Carlo estimate as a ground-truth latent property. It is conditional on the chosen sampling policy and approximate because `M` is finite.

### Sudoku verifier contract

A board is correct only when all are true:

- Exactly 81 values are present in the expected format.
- Every cell contains a digit 1 through 9.
- Every original clue remains unchanged.
- Each of the nine rows, columns, and 3x3 boxes contains digits 1 through 9 exactly once.

Malformed, incomplete, or inconsistent decodes are incorrect. Where multiple solutions might be possible, rule validity and clue preservation should be primary; comparison to one reference solution alone can incorrectly reject alternate legitimate solutions. Confirm dataset puzzle uniqueness separately.

Never use a reference solution as an input feature.

---

## 12. Probe Models and Baselines

Begin with low-capacity probes. Complexity must be justified by held-out gains.

| Model | Inputs | Role |
|---|---|---|
| Class prevalence | None beyond training prevalence | Sanity baseline |
| Level-only classifier | `k` | Tests whether progress alone predicts failure |
| Input difficulty classifier | Puzzle features only | Controls for easier/harder puzzles |
| Partial-board heuristic | Current parse/validity/conflicts | Cheap, interpretable baseline |
| Code prediction entropy | Available logits at `k` | Uncertainty baseline, if technically available |
| Partial decoded-board logistic probe | Board features at `k` | Checks whether latent probes add value |
| Linear latent probe | Pooled cumulative latent at `k` | Main scientific baseline |
| Linear code-index probe | Code summaries or embeddings at `k` | Representation comparison |
| Small MLP probe | Same features as linear probe | Controlled nonlinear extension |
| Temporal probe (later) | Features from levels 1..k | Tests whether history adds signal |
| Shuffled-label probe | Shuffled training labels | Leakage/sanity control |

**Important statistical control:** Train level-specific and shared-level versions, but use the **same underlying train/validation/test puzzle IDs**. Do not count each of 12 levels as an independent test example when estimating uncertainty.

### Training protocol

1. Collect a training dataset of complete trajectories from frozen NCM.
2. Split by `puzzle_id` **before feature scaling, fitting, hyperparameter tuning, or calibration**.
3. Fit scalers on the training split only.
4. Train regularized logistic regression first (e.g., L2 with balanced and unbalanced alternatives).
5. Choose hyperparameters on validation puzzles.
6. Calibrate risk scores on separate held-out calibration puzzles if data volume permits.
7. Fix model and thresholds before reporting results on untouched test puzzles.
8. Bootstrap confidence intervals at the **puzzle level**, not the level-record level.
9. Report both per-level sample counts and unique puzzle counts.

For the deterministic default configuration, each puzzle usually has one deterministic trajectory. That is sufficient for an initial correctness probe but does not produce within-puzzle counterfactual variation. If later sampling multiple trajectories per puzzle, split by puzzle identity so nearly identical instances never leak across splits.

---

## 13. Experiment Plan

### Phase 0: Reproduce baseline (mandatory)

**Purpose:** Verify model, dataset, parser, and generation settings.

**Deliverables:** Baseline logs, manifest, unit-tested Sudoku verifier, run script.

**Exit condition:** Reproduction works reliably; deviations from reported official results are investigated and documented rather than ignored.

### Phase 1: Full-level observational dataset

**Purpose:** Understand partial decoded boards and collect candidate probe inputs.

**Work:**

- Decode all 12 cumulative latents of a hard-Sudoku trajectory using upstream decoding behavior.
- Record exact current correctness and final correctness.
- Record per-level timings and representational summaries.
- Measure how many trajectories self-correct, remain wrong, become wrong late, or are correct throughout later levels.
- Check that the reconstructed final output matches the original uninstrumented result.

**Deliverables:** Versioned trajectory Parquet, plots of correctness by level, transition matrix, instrumentation overhead report.

### Phase 2: Offline correctness probes

**Purpose:** Evaluate predictive signal without changing generation.

**Work:**

- Train the baselines and latent-state probes.
- Evaluate ROC-AUC, PR-AUC, balanced accuracy, Brier score, calibration and per-level performance.
- Set explicit operating points at a validation-selected false-positive budget (for example 5% and 10%, as experimental targets, not guarantees).
- Compare levels early, middle, and late to check whether signal emerges with refinement.
- Examine input-only and decoded-only controls to isolate any extra value from latent features.

**Deliverables:** Held-out evaluation, confidence intervals, calibration curves, probe artifacts, and error analysis.

**Go/no-go gate:** If latent probes do not outperform simpler controls by a practically meaningful amount, document the negative result and reconsider the need for complex instrumentation.

### Phase 3: Counterfactual prefix branching

**Purpose:** Distinguish recoverability from one-trajectory labels.

**Prerequisite:** The NCM generator must support **tested resumption** from a selected prefix level. The current public `generate()` path is not assumed to expose this feature directly.

**Work:**

1. Create a minimal, isolated fork or local patch that records all required NCM continuation state.
2. Hold a prefix of generated codes fixed at level `k`.
3. Sample independent suffixes with a **nonzero** temperature and documented top-k/top-p policy.
4. For each prefix, run `M` suffixes, evaluate each one, and estimate `r_k`.
5. Use confidence intervals for small `M`; report conditional risk rather than a false exact value.
6. Compare risk prediction from codes, latents, and decoded partial boards.
7. Ensure reusing a prefix does not accidentally re-sample or alter its earlier codes.

**Critical scientific separation:** Because the official hard-Sudoku baseline uses `temperature: 0.0`, do **not** compare a new stochastic policy's raw accuracy with the official deterministic solve rate without clearly separating the configurations. The branching experiment is a new experimental condition.

**Deliverables:** Branching test suite, prefix-risk benchmark, plots of recoverability over levels, sample-cost audit.

### Phase 4: Online intervention

**Purpose:** Test whether predictive risk is *actionable*.

Compare the following policies under the **same measured cost budget**:

- Always complete the full NCM hierarchy.
- Fixed-budget unconditional re-sampling/restarts.
- Cheap Sudoku verifier with best-of-N sampling.
- Heuristic confidence/partial-output policies.
- Probe-triggered full restart from scratch.
- Probe-triggered suffix resampling from an earlier cached prefix (only after proven correct).
- Probe-triggered continued generation with verifier (when supported).

Track all abandoned generation work, probe calls, restarts, verifier costs, memory, and total latency. An offline simulation is allowed for policy selection but **not** as the final evidence of online gains.

**Deliverables:** True live intervention benchmark, speed/accuracy frontiers, cases where probing makes results worse.

### Phase 5: Generalize to natural language

**Purpose:** Assess whether the method helps AI trustworthiness beyond exact-verifiable puzzles.

- Begin with official German-to-English translation and XSum summarization checkpoints.
- Define independently labeled error targets: changed/negated meaning, wrong numerical quantities, named-entity substitutions, unsupported statements, or source contradiction.
- Prefer reference-grounded exact constraints for a small controlled subset before broad semantic scoring.
- If using an LLM judge, report evaluator agreement with human labels and susceptibility to judging its own generated text.
- Compare latent probes to partial-text semantic-checker baselines.
- Do not equate BLEU or ROUGE alone with factual truthfulness.

**Deliverables:** Carefully scoped factual-reliability benchmark, annotation protocol, cross-task comparisons.

### Phase 6: Optional user interface

**Only after Phase 2 shows useful results.** A React interface can visualize generated levels, decoded boards, probability trajectories, alternate completions, and which interventions were chosen. This is a demonstration and debugging tool, not the first milestone or a substitute for a rigorous report.

---

## 14. Metrics and Statistical Reporting

### Prediction

- **AUROC:** Overall discrimination between eventual success and failure.
- **AUPRC:** Especially useful when failures are relatively infrequent; always report failure prevalence.
- **Brier score and calibration plots:** Probability reliability.
- **False-positive rate at chosen recall/threshold:** How frequently good trajectories are unnecessarily flagged.
- **Recall at a fixed false-positive budget:** Practical detection sensitivity.
- **Per-level lead time:** Levels and milliseconds remaining when a failure is detected.
- **Incremental lift over input-only baseline:** Helps distinguish trajectory information from puzzle difficulty.

### Intervention

- **Solved rate:** Percentage of complete, valid boards.
- **Cost per correct result:** End-to-end GPU work or wall-clock cost divided by number of correct outputs.
- **Latency percentiles:** Median, p90, p95 when enough samples exist.
- **Recovery rate:** Fraction of otherwise-failing cases rescued by a policy, evaluated using paired and budget-matched comparison.
- **Collateral damage:** Fraction of otherwise-correct cases harmed by interventions.
- **Monitoring overhead:** Model hook, feature extraction, probe, verifier, tensor transfer, and logging time.

### Counterfactual risk

- **Brier/MAE of predicted `r_k`** compared with Monte Carlo frequency.
- **Uncertainty for sampled completion proportions**, e.g., Wilson intervals or hierarchical bootstrap.
- **Number of branches and GPU cost per evaluated prefix.**

### Analysis rules

- Use predetermined train/validation/test splits by puzzle identity.
- Bootstrap at puzzle identity, not at individual level or branch record.
- Disclose all model/config/seed selections; avoid picking the best result over many configurations without adjustment.
- Measure paired differences on the same held-out puzzles where possible.
- Report failure prevalence, sample size, confidence intervals, and both positive and negative findings.
- Measure actual elapsed time using CUDA synchronization and warmup; report batch size and GPU type.
- Do not use guessed speedups or extrapolate from skipped levels alone.

---

## 15. Interface Contracts (Proposed, Not Upstream API)

The experiment runner should expose stable, testable interfaces regardless of how upstream functions change.

```python
from typing import Protocol

class LevelObserver(Protocol):
    def on_level(self, state: "LevelState") -> None: ...

class FailureProbe(Protocol):
    def predict_failure_probability(self, state: "LevelState") -> float: ...

class InterventionPolicy(Protocol):
    def decide(self, state: "LevelState", risk: float) -> str:
        """Return one of: continue, restart, resample_suffix, verify, abstain."""
```

These are design sketches. Use typed domain objects instead of raw dictionaries wherever practical. For large tensors, record tensor references or compact pooled features; avoid silently moving GPU tensors to CPU at each level during timing-critical runs.

**Safe mode:** Disable probes and interventions and reproduce upstream full-depth generation exactly.

**Research mode:** Collect full depth with internal representations and gold labels.

**Enforcement mode:** Observe each level online and perform only interventions supported and tested at the pinned upstream commit.

---

## 16. Testing and Quality Gates

### Required unit tests

- Sudoku verifier rejects duplicate digits, changed clues, malformed text, missing cells, and inconsistent subgrids.
- Verifier accepts valid solutions, including alternative valid completions when puzzle uniqueness is not guaranteed.
- Partial decoder returns the same final text/board as original full-depth evaluation.
- Probe features available at level `k` are unaffected by modifying data belonging only to future levels.
- Puzzle-level splits never share the same puzzle across train/validation/test.
- Feature scalers and calibration never fit on test data.
- Shuffled-label probes yield near-chance behavior in sufficiently large evaluations.
- Disabling instrumentation and interventions restores baseline generation outputs.
- Prefix resume reproduces an uninterrupted continuation under identical RNG state, if the continuation implementation supports that equivalence.
- Stochastic branch seeds produce recorded reproducible outputs.
- Equal-compute budgeting counts failed retries and monitoring work.

### Acceptance criteria by release

**v0.1:** Checkpoint loads; official smoke evaluation reproduced; Sudoku validator tested; environment and exact upstream SHA logged.

**v0.2:** Full 12-level trajectories recorded for a subset, final output matches baseline, no test leakage, transition analysis generated.

**v0.3:** Probes trained with input-only and decoded-output controls; calibration and held-out metrics published with uncertainty.

**v0.4:** Counterfactual prefix branching reproduces resume behavior and returns plausible Monte Carlo risk estimates under explicit stochastic conditions.

**v0.5:** Live interventions benchmarked at fixed cost against equally strong unconditional retry, verifier, and simple heuristic baselines.

**v1.0:** Research report with limitations, reproducible scripts, checkpoint/config provenance, and optional viewer. Natural-language evaluation is a stretch goal, not an assumed result.

---

## 17. Risks, Failure Modes, and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| No early predictive signal | NCM states may not expose useful correctness information | Input-only and shuffled controls; report negative result |
| Difficulty confounding | Probe learns which puzzles are hard rather than trajectory risk | Input-only baseline, grouped splits, repeated continuations later |
| Class imbalance | High Sudoku success can make accuracy meaningless | Report failure prevalence, AUPRC, recall/FPR, calibration |
| Intermediate self-correction | A wrong partial board can become correct | Target eventual correctness; classify repair trajectories separately |
| Causal overclaiming | Correlated latent features do not prove causal mechanisms | Use counterfactual resampling/intervention, distinguish association from causation |
| Deterministic branching illusion | Temperature 0 yields no genuine alternative suffixes | Separate stochastic continuation configuration and validate randomness |
| Evaluation leakage | Twelve records per puzzle and sampled branches can leak across splits | Split by puzzle before training; bootstrap by puzzle |
| Hook overhead/OOM | Saving full activations may exhaust GPU memory and distort speed | Select few layers, pooled stats, streaming storage, batched analysis |
| Post-hoc policy claims | Offline traces omit actual cost and state behavior | Require online controller for real performance claims |
| Weak intervention baselines | Expensive learned policy may beat only trivial full-depth baseline | Compare against verifier, unconditional retries, fixed budgets |
| Semantic label ambiguity | Factuality of natural-language outputs is harder to label than Sudoku | Start with controlled exact factual constraints and documented annotation |
| Safety overclaim | Structural errors are not policy violations | Distinguish reliability, factuality, and safety experiments |
| Upstream code drift | Changing repository changes model semantics | Git submodule pin, checkpoint hashes, output equivalence tests |

---

## 18. Reproducibility, Security, and Responsible Research

- Use public checkpoints and synthetic/benchmark input data; do not insert real private user records into evaluation runs.
- For later safety testing, use sanitized and harmless controlled cases. Avoid publishing actionable exploit payloads or hidden system information.
- Record upstream commit, artifact digests, config snapshots, random seeds, data versions, probe training configuration, and evaluation code SHA.
- Write manifests and small result summaries to version control; use Git LFS or external artifact storage for larger outputs if needed.
- All claims must distinguish **observed results**, **paper-reported upstream results**, and **untested hypotheses**.
- Implement a clean README with hardware caveats and commands; mark unrun scripts as unvalidated.
- Document the MIT upstream license and any modifications to upstream code.
- Do not present this system as a production-ready safety certification or guarantee; false negatives are expected.

### Required report artifacts

```text
results/reports/
  baseline_reproduction.md
  level_trajectory_analysis.md
  probe_evaluation.md
  counterfactual_recoverability.md     # later
  live_intervention_benchmark.md       # later
  negative_results_and_limitations.md
```

Each report should point to an exact manifest, command, code revision, and data hash.

---

## 19. Implementation Roadmap and Priorities

| Milestone | Deliverable | Gate |
|---|---|---|
| M0: Reproduce | GPU environment + upstream Sudoku | Official code runs and logs reproduce |
| M1: Observe | Per-level codes, latents, boards | Final output matches baseline exactly |
| M2: Label | Validator and correct/incorrect transitions | Unit tests and manual sample spot checks pass |
| M3: Probe | Input-only, decoded-only, latent probes | Untouched test metrics, uncertainty, no leakage |
| M4: Branch | Resume and stochastic suffixes | Reproducible branches, frozen-prefix test |
| M5: Intervene | Online probe + cost-matched comparison | Actual end-to-end cost and solved rate measured |
| M6: Generalize | Source-grounded translation/XSum labels | Semantic task evaluation independently validated |
| M7: Visualize | Optional interactive web explorer | Research conclusions already documented |

**Priority recommendation:** Finish **M0-M3** first. Do not commit to custom generation surgery for M4 until M3 shows interesting predictive information, or a specific counterfactual result is independently valuable.

---

## 20. Immediate Work Order for Codex

Give Codex this document as `DESIGN.md` and instruct it to follow these steps:

1. Read the entire design. Inspect the actual `third_party/ncm` source and verify every CLI/API assumption at the pinned commit.
2. Initialize the repository and add a pinned NCM submodule, or use the existing repository if already initialized. Preserve existing user changes and do not delete work.
3. Set up a working Python environment; verify CUDA if GPU evaluation is intended.
4. Download **only** the necessary hard-Sudoku checkpoint and data, documenting exact file paths.
5. Reproduce a small official baseline and record the logs, manifest, exact arguments, and checksum information.
6. Implement a correct Sudoku parser and validator with adversarial unit tests.
7. Add an observational adapter collecting all partial reconstructed levels without changing final generation. Confirm last-level output equivalence.
8. Save a small versioned trajectory dataset and produce initial descriptive plots.
9. Only then implement input-only, decoded-output, and regularized linear latent probes, with puzzle-grouped splits.
10. Report metrics, caveats, and whether the latent probe adds value. **Do not implement counterfactual branching, live interventions, or a UI until these steps pass.**

**Important Codex instructions:**

- Prefer modifying project wrappers over upstream model code. Any necessary upstream patch must be minimal, reviewed, and regression-tested.
- Never claim that a command, training job, or accuracy result succeeded unless it was run and recorded.
- If blocked by hardware, checkpoint access, or dependency mismatch, leave a documented reproducible blocker and complete unit-testable local components instead.
- Do not silently substitute a different architecture for NCM.
- Use the same definitions, split rules, and source hashes across Concept Firewall and Anytime NCM if both are developed.
- Optimize for clear scientific evidence, not a flashy app.

### Expected initial outputs from Codex

```text
README.md
DESIGN.md
pyproject.toml
configs/sudoku_smoke.yaml
src/concept_firewall/upstream_adapter.py
src/concept_firewall/level_capture.py
src/concept_firewall/sudoku_labels.py
tests/test_sudoku_labels.py
tests/test_partial_reconstruction.py
results/manifests/<run-id>.json
docs/reproduction_log.md
```

If no GPU is available, a valid partial milestone is a tested verifier, validated data schema, repository skeleton, and an explicit statement that official model inference has not run.

---

## 21. Research Decision Criteria

Before expanding the scope, answer:

1. Does any intermediate representation reliably predict final correctness on **unseen puzzles**?
2. Does it outperform an input-only difficulty model and a partial-board checker?
3. Is this signal available sufficiently early, with enough remaining computation to matter?
4. Is it calibrated well enough to support a useful false-alarm budget?
5. Under a separate stochastic policy, can high-risk prefixes still recover through alternative suffixes?
6. Can an actual intervention beat a simple verifier and unconditional retries at equal total cost?
7. Does the result generalize beyond Sudoku, or is it strictly structural correctness research?

**If 1 or 2 fails:** Publish a careful negative result or change the representation/task; do not claim a useful firewall.  
**If 1-4 succeed but 6 fails:** Report an interesting diagnostic probe, not a deployment-ready defense.  
**If 1-6 succeed:** Investigate factual reliability with independent labels and consider the stronger AI safety framing.

---

## 22. References and Primary Links

1. Kumbong et al., *Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation* (2026): https://arxiv.org/abs/2610.14162
2. Stanford Hazy Research, NCM explanation and interactive demonstration: https://hazyresearch.stanford.edu/blog/2026-10-12-ncm
3. Official NCM source (MIT): https://github.com/HazyResearch/ncm
4. Official evaluator: https://github.com/HazyResearch/ncm/blob/main/scripts/eval_shard.py
5. Official generator: https://github.com/HazyResearch/ncm/blob/main/models/next_concept.py
6. Official hard-Sudoku config: https://github.com/HazyResearch/ncm/blob/main/config/eval/sudoku-hard.yaml
7. Chiu and Liu, *Probing Functional Correctness in Diffusion Language Models*, ACL Student Research Workshop 2026: https://aclanthology.org/2026.acl-srw.15/
8. Probe source code and baseline methodology: https://github.com/guan404ming/dlm-probing
9. Yu and Liu, *Real-time hallucination detection and intervention in medical LLMs via calibrated hidden-state probes* (2026): https://www.sciencedirect.com/science/article/pii/S153204642600105X
10. NCM checkpoint collection: https://huggingface.co/hazyresearch/ncm-checkpoints
11. NCM datasets: https://huggingface.co/datasets/hazyresearch/ncm-datasets
12. Official PyTorch installation: https://pytorch.org/get-started/locally/

**Research status at authoring:** A focused prior-art review supports this as a reasonable NCM-specific research investigation, **not** a confirmed novel paper contribution. Recheck publications, issues, and related code before submitting any originality claim.

---

## Appendix A. Proposed First Results Table

The table below is a **report template**, not actual measured results.

| Level | Unique test puzzles | Failure prevalence | Input-only AUROC | Decoded-board AUROC | Latent probe AUROC | Latent probe AUPRC | Mean time to level |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 6 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 9 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 11 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

The final level is useful for diagnosis but cannot support *early* prevention if the output is already complete. Show it separately as a post-generation upper-bound reference.

## Appendix B. Candidate Visualization (Later)

A future Concept Firewall interface may contain:

- A Sudoku input and a 12-stage reconstruction timeline.
- Per-level decoded board with color-coded conflicts and changes.
- Per-level predicted final-failure probability with confidence/calibration labels.
- A branching explorer showing controlled suffix continuations from a selected prefix.
- Policy replay comparing normal generation and probe-based interventions under equal budget.
- Side-by-side links to relevant Anytime NCM generation trajectories.

All visualizations must clearly label actual measurements versus explanatory mock data. Build this UI **after** scientific baselines are validated.
