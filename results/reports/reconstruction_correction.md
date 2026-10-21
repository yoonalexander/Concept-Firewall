# Superseded native-length reconstruction experiment

Initial collection runs `20261021T014240800481Z-collection` and `20261021T014611959101Z-collection` decoded upstream `z_levels` directly. At this source revision, these representations have lengths 1..89, so intermediate decoder outputs are short strings, not full candidate boards. All pre-final boards therefore failed shape validation. The initial plot and “repair” counts reflect this formatting fact and do not establish board recovery dynamics. Initial probe run `20261021T014827648866Z-probes` uses this unsuitable decoded-output control and is superseded. Do not use it for the intended scientific comparison.

The official baseline runs and final-output equivalence measurements remain valid. Source inspection also found the `z_hats` list aliases the mutable final accumulator, so using that list as-is would leak future information. No upstream source was changed.

The corrected wrapper uses the upstream quantizer's `get_next_autoregressive_input` and embeddings to accumulate each observed prefix at full sequence length, cloning before advancing. The final accumulator must match the original final path exactly. Actual-source tests assert full sequence length, final equality, separate storage and independence from future code mutations. Feature version `sudoku-full-prefix-v2` and manifest contract `full-cumulative-prefix-v2` distinguish the corrected data. The original frozen probe protocol and puzzle partitions remain unchanged; earlier probe metrics were not used to choose new models, levels or thresholds.

Earlier runs and their source snapshot are retained for audit. Only corrected full-prefix runs should be cited for intermediate boards and probe comparisons.
