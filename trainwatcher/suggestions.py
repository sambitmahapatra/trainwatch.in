"""Suggestion mapping for deterministic analysis results."""

from __future__ import annotations

from typing import Any, Dict, List


SUGGESTION_MAP = {
    "overfitting": [
        "Enable early stopping to stop near the best validation checkpoint.",
        "Increase regularization such as dropout or weight decay.",
        "Reduce the number of training epochs or add more data augmentation.",
    ],
    "plateau": [
        "Reduce the learning rate or enable a scheduler.",
        "Increase patience before stopping so the optimizer can recover.",
        "Review model capacity or feature quality if progress stays flat.",
    ],
    "diverging": [
        "Lower the learning rate and retry from a stable checkpoint.",
        "Check input normalization and loss scaling for unstable batches.",
        "Inspect data quality and batch composition for outliers.",
    ],
    "normal_convergence": [
        "Keep checkpointing the best validation model.",
        "Enable early stopping to avoid drifting past the optimum.",
        "Run a short hyperparameter sweep around the current settings.",
    ],
    "mixed_signal": [
        "Log more validation metrics to make behavior easier to interpret.",
        "Run a few more epochs before acting on ambiguous signals.",
    ],
    "insufficient_data": [
        "Log both training and validation metrics each epoch.",
        "Capture epoch numbers so TrainWatcher can detect trends.",
    ],
    "class_index_mismatch": [
        "Set the final output dimension to match the dataset label count.",
        "Verify that target labels are in the expected range for the loss function.",
        "Check any class remapping or label encoding step before training.",
    ],
    "cuda_oom": [
        "Reduce batch size or input resolution and retry.",
        "Enable mixed precision or gradient accumulation if available.",
        "Check for tensors that remain on GPU longer than necessary.",
    ],
    "cuda_device_assert": [
        "Inspect label ranges, tensor indexing, and loss inputs for invalid values.",
        "Restart the kernel after fixing the issue because the CUDA context is now invalid.",
        "Reproduce the failing step on CPU to get a clearer stack trace.",
    ],
    "shape_mismatch": [
        "Print tensor shapes before the failing layer or loss call.",
        "Verify flattening, channel count, and final layer dimensions.",
        "Confirm the loss function expects the same output and target shapes you provide.",
    ],
    "device_mismatch": [
        "Move the model and every tensor in the batch to the same device.",
        "Check custom tensors created inside the training loop for missing `.to(device)` calls.",
        "Keep metric accumulation on CPU if it does not need GPU execution.",
    ],
    "missing_file": [
        "Verify dataset, checkpoint, and config paths before training starts.",
        "Use absolute paths or resolve paths relative to the project root.",
        "Check that the runtime environment has permission to read the required files.",
    ],
    "dependency_error": [
        "Install the missing package in the active environment and restart the kernel.",
        "Verify that the notebook kernel points to the intended Python environment.",
        "Pin dependency versions if the project relies on a known stack.",
    ],
    "runtime_error": [
        "Inspect the full traceback to locate the first failing operation.",
        "Re-run the smallest reproducible step before restarting the full training job.",
        "Log a few more intermediate metrics or shapes around the failing section.",
    ],
}


def suggest(analysis: Dict[str, Any], limit: int = 3) -> List[str]:
    """Return concise next-step suggestions for a rule result."""
    status = str(analysis.get("status") or "mixed_signal")
    suggestions = list(SUGGESTION_MAP.get(status, SUGGESTION_MAP["mixed_signal"]))
    return suggestions[:limit]


def attach_suggestions(analysis: Dict[str, Any], limit: int = 3) -> Dict[str, Any]:
    """Return a copy of analysis with suggestion text attached."""
    enriched = dict(analysis)
    enriched["suggestions"] = suggest(analysis, limit=limit)
    return enriched
