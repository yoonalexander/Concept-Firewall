# Upstream compatibility

Pinned source: HazyResearch/ncm `c70274273f489abc73832b2b98584a8483b6b203`, MIT (see `third_party/ncm/LICENSE`). No upstream modifications.

Source inspection confirms `evaluate.py` accepts `--config`, `--checkpoint-dir`, `--data-dir`, `--gpus`, `--n`, `--out` and forwards `--bs` to `scripts/eval_shard.py`. The latter loads tokenizers and generator checkpoints, calls `generate(None, context, temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0, cfg_null_eos=None)`, then calls `idx_to_zhats(..., return_zlevels=True)` and decodes the final cumulative latent with argmax. Frequency and adjacency penalties are absent in the released hard-Sudoku configuration. No callback or prefix-resume API is assumed.

The twelve level lengths are `1,2,4,6,9,13,18,26,37,50,67,89`. Latents returned for earlier levels have that level's sequence length; they are cumulative tokenizer reconstructions, not transformer hidden states. Code IDs are categorical. Post-hoc collection is deliberately separate from generation.

**Important correction from the supplied design:** passing those short `z_levels` straight to the decoder produces short outputs, not full candidate boards. `z_hats` cannot be substituted directly because its entries alias the final mutable accumulator. Full-board observation instead calls the upstream quantizer's `get_next_autoregressive_input` on each observed level embedding and clones the full-size accumulator before advancing. Tests assert full length, storage independence, future-code independence and exact final equality. This is an observational wrapper, with no changes to generation or upstream code. See `results/reports/reconstruction_correction.md`; initial native-length experiments are superseded.

`SudokuTokenizer` uses blank `0` -> `_`, digits `1..9`, separator token `10` -> `|`, BOS token `11` -> `<BOS>`. EOS and PAD are `None`. Inputs in the pinned data have 91 tokens: BOS, 89 board tokens, BOS. Decoding inputs with `skip_special_tokens=True` removes BOS, preserving strict board structure. Predictions are decoded with the official rules. The verifier rejects malformed delimiters, extra cells and missing cells.

The upstream `solved` metric is equality against the supplied reference, and `valid` checks Sudoku constraints without the original clues. Our final-valid label additionally enforces every original clue and accepts alternative valid solutions. Reports must distinguish these definitions.

Artifact layout correction: examples using Hub path `sudoku-hard/*` yield no task files. Actual paths are `sudoku/hard/*`. Reviewed revisions and expected hashes are in `src/concept_firewall/artifacts.py` and `results/manifests/artifacts.json`. Hashes are checked before deserializing public benchmark pickles or upstream checkpoints.
