# Source and artifact notices

This package records a scoped research study, with no claim of novelty, production safety, or completion of M4–M7.

- **NCM source:** HazyResearch/ncm at `c70274273f489abc73832b2b98584a8483b6b203`. Its MIT license, including the original copyright notice, is retained at [third_party/ncm/LICENSE](third_party/ncm/LICENSE). Source packages include this pinned source and license; Python wheels contain only the Concept Firewall package.
- **Checkpoint card:** the [pinned model card](https://huggingface.co/hazyresearch/ncm-checkpoints/blob/d342ce8aaea58830eef3b8ad473664673e41f692/README.md) declares `license: mit`.
- **Dataset card:** the [pinned dataset card](https://huggingface.co/datasets/hazyresearch/ncm-datasets/blob/6580ba41a4b0a976dde876fbe84d25327617b0e6/README.md) declares `license: mit`. This study uses the hard-Sudoku files only; it makes no licensing assessment of other tasks in that repository.
- Checkpoints and official dataset files are excluded from the evidence ZIP. The `download` command retrieves the four pinned files and verifies their exact SHA-256 and sizes. Derived evidence includes Sudoku inputs, model outputs, features, and fitted probes.
- Dependencies retain their own licenses and are installed separately. `requirements.lock` records the tested Windows environment; it is neither a cross-platform resolver lock nor a dependency-license inventory.
- No new license for the original Concept Firewall code or reports is granted by this packaging step. The repository owner has not selected a project-wide license. Public availability does not itself grant redistribution rights to that original material.

The two pinned Hub cards were inspected on October 23, 2026. These notices identify the checked source statements; they do not expand any upstream license or declare a publication-ready licensing review of every dependency.
