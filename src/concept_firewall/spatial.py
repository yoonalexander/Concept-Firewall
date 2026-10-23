"""Two frozen, label-independent spatial summaries of an observed prefix."""
from __future__ import annotations

import math


def rademacher_projection(input_dimension: int, output_dimension: int, seed: int):
    import numpy as np
    if input_dimension < 1 or output_dimension < 1 or seed < 0:
        raise ValueError("Projection dimensions must be positive and seed nonnegative")
    signs = np.random.default_rng(seed).integers(0,2,size=(input_dimension,output_dimension),dtype=np.int8)
    return (signs.astype(np.float32)*2-1)/math.sqrt(output_dimension)


def reconstruct_prefix(vq, codes_prefix, level: int):
    """Consume exactly the observed prefix. Later codes are rejected at entry."""
    import torch
    if type(level) is not int or not 1 <= level <= len(vq.levels):
        raise ValueError("Invalid prefix level")
    if codes_prefix.ndim != 2 or codes_prefix.shape[0] < 1 or codes_prefix.shape[1] != sum(vq.levels[:level]):
        raise ValueError("Supply exactly the observed prefix, without future codes")
    with torch.no_grad():
        cumulative = torch.zeros(codes_prefix.shape[0],vq.levels[-1],vq.embed_dim,device=codes_prefix.device)
        offset=0
        for index,length in enumerate(vq.levels[:level]):
            current=codes_prefix[:,offset:offset+length]
            embedding=vq.embeddings[index](current)
            cumulative,_=vq.get_next_autoregressive_input(index,cumulative,embedding)
            offset+=length
        return cumulative.clone()


def spatial_summaries(latent, row_projection, cell_projection):
    import torch
    if latent.ndim != 3 or latent.shape[1] != 89:
        raise ValueError("Expected full 89-token Sudoku latent")
    if not torch.isfinite(latent).all():
        raise ValueError("Latent must be finite")
    indices=[r*10+c for r in range(9) for c in range(9)]
    cells=latent[:,indices,:].float()
    rows=cells.reshape(latent.shape[0],9,9,latent.shape[2]).mean(dim=2)
    if row_projection.shape[0] != rows.shape[1]*rows.shape[2] or cell_projection.shape[0] != cells.shape[1]*cells.shape[2] or row_projection.shape[1] != cell_projection.shape[1]:
        raise ValueError("Frozen projection shape mismatch")
    return rows.flatten(1) @ row_projection, cells.flatten(1) @ cell_projection
