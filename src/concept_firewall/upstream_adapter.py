"""Thin, observational adapter for the pinned official hard-Sudoku evaluator.

ML dependencies are imported only when loading or running a model. Generation
and final decoding follow ``scripts/eval_shard.py``; this module adds no hooks,
sampling algorithm, prefix-resume path, trained probe, or live intervention.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import math
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .timing import timed_call


PINNED_UPSTREAM_COMMIT = "c70274273f489abc73832b2b98584a8483b6b203"
HARD_SUDOKU_LEVELS = (1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89)


class UpstreamUnavailableError(RuntimeError):
    """The requested source, dependency, artifact, or device is unavailable."""


class UnsupportedConfigurationError(ValueError):
    """A setting would require behavior not implemented by this adapter."""


@dataclass(frozen=True)
class GenerationSettings:
    temperature: float = 0.0
    top_k: int = 0
    top_p: float = 1.0
    cfg_scale: float = 0.0
    cut_at_eos: bool = True

    def __post_init__(self) -> None:
        for name in ("temperature", "top_p", "cfg_scale"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.temperature < 0 or self.cfg_scale < 0:
            raise ValueError("temperature and cfg_scale must be nonnegative")
        if type(self.top_k) is not int or self.top_k < 0:
            raise ValueError("top_k must be a nonnegative integer")
        if not 0 <= self.top_p <= 1:
            raise ValueError("top_p must lie in [0, 1]")
        if type(self.cut_at_eos) is not bool:
            raise ValueError("cut_at_eos must be a boolean")

    @classmethod
    def from_config(cls, generation: Mapping[str, Any]) -> GenerationSettings:
        # These require upstream token-picking/L0 logic beyond this Sudoku path.
        for name in ("frequency_penalty", "frequency_deficit"):
            if float(generation.get(name, 0.0)) != 0.0:
                raise UnsupportedConfigurationError(f"unsupported generation setting: {name}")
        for name in ("adjacency_penalty", "frequency_allowance", "level0_unigram"):
            if generation.get(name):
                raise UnsupportedConfigurationError(f"unsupported generation setting: {name}")
        return cls(
            temperature=float(generation.get("temperature", 1.0)),
            top_k=int(generation.get("top_k", 1)),
            top_p=float(generation.get("top_p", 0.0)),
            cfg_scale=float(generation.get("cfg_scale", 0.0)),
            cut_at_eos=generation.get("cut_at_eos", True),
        )


@dataclass(frozen=True)
class ReconstructedLevel:
    """Immutable exported observations for a whole batch at one level.

    ``decode_ms`` measures current decoder, pooling, transfer, and text work.
    The shared ``idx_to_zhats`` call is included only in total reconstruction
    timing. Neither measurement is incremental generator time.
    """

    level: int
    codes_prefix_by_sample: tuple[tuple[tuple[int, ...], ...], ...]
    texts: tuple[str, ...]
    pooled_latents: tuple[tuple[float, ...], ...]
    decode_ms: float


def _torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ImportError as exc:
        raise UpstreamUnavailableError("PyTorch is required for NCM inference; install the ML environment") from exc


def _activate_upstream(root: Path) -> None:
    for relative in ("models/next_concept.py", "tokenization/vqvae_tokenizer.py"):
        if not (root / relative).is_file():
            raise UpstreamUnavailableError(f"missing pinned NCM source: {root / relative}")
    # Upstream uses top-level models/tokenization/utils and Hydra class strings.
    # Reject an already imported different checkout rather than mixing versions.
    for name in ("models", "tokenization", "utils"):
        module = sys.modules.get(name)
        filename = getattr(module, "__file__", None)
        paths = list(getattr(module, "__path__", ())) if module else []
        candidates = [Path(filename).resolve()] if filename else [Path(p).resolve() for p in paths]
        if module is not None and (not candidates or any(not p.is_relative_to(root) for p in candidates)):
            raise UpstreamUnavailableError(f"{name} is already imported from another source; use a fresh Python process")
    source = str(root)
    if source not in sys.path:
        sys.path.insert(0, source)


class NCMAdapter:
    """Wrap frozen upstream components; construction also supports unit fixtures."""

    def __init__(
        self, tokenizer: Any, generator: Any, *, prefix_len: int,
        generation_settings: GenerationSettings | None = None,
        device: object = "cpu", checkpoint_paths: Mapping[str, Path] | None = None,
    ) -> None:
        if type(prefix_len) is not int or prefix_len < 1:
            raise ValueError("prefix_len must be a positive integer")
        self.tokenizer = tokenizer
        self.generator = generator
        self.prefix_len = prefix_len
        self.device = device
        self.generation_settings = generation_settings or GenerationSettings()
        self.levels = tuple(int(value) for value in tokenizer.vqvae.vq.levels)
        if not self.levels or any(value < 1 for value in self.levels):
            raise ValueError("tokenizer must expose positive hierarchy lengths")
        self.checkpoint_paths = MappingProxyType(dict(checkpoint_paths or {}))

    @classmethod
    def load(
        cls, upstream_root: str | Path, config_path: str | Path,
        checkpoint_dir: str | Path, *, device: str = "cuda",
    ) -> NCMAdapter:
        """Load the two configured checkpoint files with upstream strict rules.

        Public checkpoint provenance and the pinned Git SHA are recorded by the
        runner. As upstream does, checkpoint loading uses ``weights_only=False``.
        Only locally selected official artifacts should be supplied here.
        """
        root = Path(upstream_root).resolve()
        config_file = Path(config_path).resolve()
        checkpoint_root = Path(checkpoint_dir).resolve()
        try:
            omega = importlib.import_module("omegaconf").OmegaConf
        except ImportError as exc:
            raise UpstreamUnavailableError("OmegaConf is required to load the upstream configuration") from exc
        config = omega.load(config_file)
        if config.get("task") != "sudoku-hard" or config.tokenizer.pre_tokenizer.get("name") != "sudoku":
            raise UnsupportedConfigurationError("only the official sudoku-hard task and Sudoku tokenizer are supported")
        settings = GenerationSettings.from_config(config.generation)
        paths = {name: checkpoint_root / str(config.checkpoints[name]) for name in ("tokenizer", "generator")}
        for name, path in paths.items():
            if not path.is_file():
                raise UpstreamUnavailableError(f"missing {name} checkpoint: {path}")
        torch = _torch()
        requested_device = torch.device(device)
        if requested_device.type not in ("cpu", "cuda"):
            raise UnsupportedConfigurationError("only explicit CPU or CUDA devices are supported")
        if requested_device.type == "cuda" and not torch.cuda.is_available():
            raise UpstreamUnavailableError("CUDA was requested but is unavailable; no CPU fallback was used")
        _activate_upstream(root)
        try:
            tokenizer_class = importlib.import_module("tokenization.vqvae_tokenizer").VQVAETokenizer
            generator_class = importlib.import_module("models.next_concept").NextConceptTransformer
        except ImportError as exc:
            raise UpstreamUnavailableError(f"an upstream NCM dependency is missing: {exc}") from exc
        config.tokenizer.vqvae.checkpoint_path = str(paths["tokenizer"])
        tokenizer = tokenizer_class.from_config(config.tokenizer)
        tokenizer.vqvae = tokenizer.vqvae.to(requested_device).eval()
        generator = generator_class(vqvae_local=tokenizer.vqvae, config=config.model).to(requested_device)
        state = torch.load(paths["generator"], map_location="cpu", weights_only=False)
        generator.load_state_dict(state["model"], strict=True)
        generator.eval()
        return cls(tokenizer, generator, prefix_len=int(config.model.prefix_len),
                   generation_settings=settings, device=requested_device, checkpoint_paths=paths)

    def prepare_context(self, items: Sequence[Sequence[int] | str]) -> Any:
        """Use evaluator truncation/padding, refusing undefined Sudoku padding."""
        if not items:
            raise ValueError("at least one input is required")
        pad = self.tokenizer.pre_tokenizer.pad_token_id
        prefixes = []
        for item in items:
            if isinstance(item, str):
                raise ValueError("supply the official pre-tokenized Sudoku inputs, not unverified text tokenization")
            ids = list(item)[:self.prefix_len]
            if any(type(value) is not int or not 0 <= value < 12 for value in ids):
                raise ValueError("Sudoku context must contain integer token IDs in [0, 11]")
            if len(ids) < self.prefix_len:
                if pad is None:
                    raise ValueError("Sudoku has no PAD token: context is shorter than the upstream prefix length")
                ids += [pad] * (self.prefix_len - len(ids))
            prefixes.append(ids)
        return _torch().tensor(prefixes, dtype=_torch().long, device=self.device)

    def generate(self, context: Any) -> Any:
        """Run the unchanged official full-depth generator without observers."""
        settings = self.generation_settings
        with _torch().no_grad():
            return self.generator.generate(
                None, context, temperature=settings.temperature,
                top_k=settings.top_k, top_p=settings.top_p,
                cfg_scale=settings.cfg_scale,
                cfg_null_eos=self.tokenizer.pre_tokenizer.eos_token_id,
            )

    def generate_timed(self, context: Any) -> tuple[Any, float]:
        measured = timed_call(lambda: self.generate(context), device=self.device)
        return measured.value, measured.elapsed_ms

    def _validate_codes(self, codes: Any) -> None:
        if len(codes.shape) != 2 or codes.shape[0] < 1 or codes.shape[1] != sum(self.levels):
            raise ValueError(f"codes must have shape (batch, {sum(self.levels)})")

    def _decode_ids(self, ids: Sequence[int]) -> str:
        ids = list(ids)
        pre_tokenizer = self.tokenizer.pre_tokenizer
        eos, pad = pre_tokenizer.eos_token_id, pre_tokenizer.pad_token_id
        if self.generation_settings.cut_at_eos and eos in ids:
            ids = ids[:ids.index(eos)]
        return pre_tokenizer.decode([value for value in ids if value not in (eos, pad)], skip_special_tokens=True)

    def _decode_latent(self, latent: Any) -> tuple[str, ...]:
        ids = self.tokenizer.vqvae.decoder(latent).argmax(-1).tolist()
        return tuple(self._decode_ids(row) for row in ids)

    def decode_final(self, codes: Any) -> tuple[str, ...]:
        """The evaluator's exact final cumulative latent + argmax decode path."""
        self._validate_codes(codes)
        with _torch().no_grad():
            _, latents = self.tokenizer.vqvae.vq.idx_to_zhats(codes, return_zlevels=True)
            return self._decode_latent(latents[-1])

    def reconstruct_levels(self, codes: Any) -> tuple[ReconstructedLevel, ...]:
        """Decode full-length cumulative prefix states, without future codes.

        Upstream's z_levels are downsampled to each level's length; decoding
        those directly produces short strings. Its z_hats list aliases the
        final mutable accumulator. Neither is a full-board prefix snapshot.
        Reuse its accumulation method and clone each prefix before advancing.
        """
        self._validate_codes(codes)
        with _torch().no_grad():
            latents = self.full_prefix_latents(codes)
            if len(latents) != len(self.levels):
                raise ValueError("upstream returned an unexpected number of cumulative levels")
            rows = codes.detach().cpu().tolist()
            result = []
            boundaries = [0]
            for length in self.levels:
                boundaries.append(boundaries[-1] + length)
            for index, latent in enumerate(latents):
                def export() -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
                    texts = self._decode_latent(latent)
                    pooled = tuple(tuple(float(value) for value in row) for row in latent.float().mean(dim=1).cpu().tolist())
                    return texts, pooled
                measured = timed_call(export, device=self.device)
                texts, pooled = measured.value
                prefixes = tuple(tuple(tuple(row[boundaries[k]:boundaries[k + 1]]) for k in range(index + 1)) for row in rows)
                result.append(ReconstructedLevel(index + 1, prefixes, texts, pooled, measured.elapsed_ms))
            return tuple(result)

    def full_prefix_latents(self, codes: Any) -> tuple[Any, ...]:
        """Snapshot upstream's full-size accumulator at each observed prefix."""
        self._validate_codes(codes)
        torch = _torch()
        vq = self.tokenizer.vqvae.vq
        with torch.no_grad():
            cumulative = torch.zeros(codes.shape[0], self.levels[-1], vq.embed_dim, device=codes.device)
            snapshots, offset = [], 0
            for index, length in enumerate(self.levels):
                embedding = vq.embeddings[index](codes[:, offset:offset + length])
                cumulative, _ = vq.get_next_autoregressive_input(index, cumulative, embedding)
                snapshots.append(cumulative.clone())
                offset += length
            return tuple(snapshots)

    def reconstruct_levels_timed(self, codes: Any) -> tuple[tuple[ReconstructedLevel, ...], float]:
        measured = timed_call(lambda: self.reconstruct_levels(codes), device=self.device)
        return measured.value, measured.elapsed_ms
