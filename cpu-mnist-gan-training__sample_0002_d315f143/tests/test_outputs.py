"""
Tests for CPU-Based MNIST GAN Training task.

Validates that the agent produced all required output files with correct
structure, content, and constraints as specified in instruction.md.
"""

import os
import json
import struct

# All output files live under /app
APP_DIR = "/app"

# ─── Helpers ───────────────────────────────────────────────────────────────

def _load_json(path):
    """Load and return parsed JSON from path, or None on failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _read_png_dimensions(path):
    """Read width and height from a PNG file's IHDR chunk.
    Returns (width, height) or (0, 0) on failure."""
    try:
        with open(path, "rb") as f:
            header = f.read(24)
            # PNG signature: 8 bytes, then IHDR chunk (4 len + 4 type + 4 width + 4 height)
            if header[:8] != b'\x89PNG\r\n\x1a\n':
                return (0, 0)
            width = struct.unpack('>I', header[16:20])[0]
            height = struct.unpack('>I', header[20:24])[0]
            return (width, height)
    except Exception:
        return (0, 0)


# ─── 1. File Existence Tests ──────────────────────────────────────────────

def test_train_script_exists():
    """The main training script must exist at /app/train_gan.py."""
    path = os.path.join(APP_DIR, "train_gan.py")
    assert os.path.isfile(path), f"train_gan.py not found at {path}"


def test_generator_pth_exists():
    """generator.pth must exist."""
    path = os.path.join(APP_DIR, "generator.pth")
    assert os.path.isfile(path), f"generator.pth not found at {path}"


def test_discriminator_pth_exists():
    """discriminator.pth must exist."""
    path = os.path.join(APP_DIR, "discriminator.pth")
    assert os.path.isfile(path), f"discriminator.pth not found at {path}"


def test_generated_samples_png_exists():
    """generated_samples.png must exist."""
    path = os.path.join(APP_DIR, "generated_samples.png")
    assert os.path.isfile(path), f"generated_samples.png not found at {path}"


def test_metrics_json_exists():
    """metrics.json must exist."""
    path = os.path.join(APP_DIR, "metrics.json")
    assert os.path.isfile(path), f"metrics.json not found at {path}"


# ─── 2. Model State Dict Validation ──────────────────────────────────────

def _load_state_dict(filename):
    """Load a PyTorch state dict from /app/<filename>."""
    import torch
    path = os.path.join(APP_DIR, filename)
    return torch.load(path, map_location="cpu", weights_only=True)


def test_generator_pth_is_valid_state_dict():
    """generator.pth must be a loadable PyTorch state dict (dict of tensors)."""
    sd = _load_state_dict("generator.pth")
    assert isinstance(sd, dict), "generator.pth did not load as a dict"
    assert len(sd) > 0, "generator.pth state dict is empty"
    import torch
    for k, v in sd.items():
        assert isinstance(v, torch.Tensor), f"Value for key '{k}' is not a Tensor"


def test_discriminator_pth_is_valid_state_dict():
    """discriminator.pth must be a loadable PyTorch state dict (dict of tensors)."""
    sd = _load_state_dict("discriminator.pth")
    assert isinstance(sd, dict), "discriminator.pth did not load as a dict"
    assert len(sd) > 0, "discriminator.pth state dict is empty"
    import torch
    for k, v in sd.items():
        assert isinstance(v, torch.Tensor), f"Value for key '{k}' is not a Tensor"


def test_generator_architecture_input_output():
    """
    Generator must map latent_size=100 -> 784.
    We verify by checking the state dict contains weight matrices
    with the correct first-layer input (100) and last-layer output (784).
    """
    sd = _load_state_dict("generator.pth")
    # Collect all weight tensors (2D) to find input/output dims
    weights = [v for v in sd.values() if v.dim() == 2]
    assert len(weights) >= 2, "Generator state dict has fewer than 2 weight matrices"

    # The first weight matrix's columns should be 100 (latent input)
    first_input_dim = weights[0].shape[1]
    assert first_input_dim == 100, (
        f"Generator first layer input dim is {first_input_dim}, expected 100"
    )

    # The last weight matrix's rows should be 784 (image output)
    last_output_dim = weights[-1].shape[0]
    assert last_output_dim == 784, (
        f"Generator last layer output dim is {last_output_dim}, expected 784"
    )


def test_discriminator_architecture_input_output():
    """
    Discriminator must map 784 -> 1.
    We verify by checking the state dict weight matrices.
    """
    sd = _load_state_dict("discriminator.pth")
    weights = [v for v in sd.values() if v.dim() == 2]
    assert len(weights) >= 2, "Discriminator state dict has fewer than 2 weight matrices"

    first_input_dim = weights[0].shape[1]
    assert first_input_dim == 784, (
        f"Discriminator first layer input dim is {first_input_dim}, expected 784"
    )

    last_output_dim = weights[-1].shape[0]
    assert last_output_dim == 1, (
        f"Discriminator last layer output dim is {last_output_dim}, expected 1"
    )


def test_generator_weights_are_nontrivial():
    """Generator weights must not be all zeros (i.e., model was actually trained)."""
    import torch
    sd = _load_state_dict("generator.pth")
    all_zero = all(torch.all(v == 0).item() for v in sd.values())
    assert not all_zero, "All generator weights are zero — model was not trained"


def test_discriminator_weights_are_nontrivial():
    """Discriminator weights must not be all zeros."""
    import torch
    sd = _load_state_dict("discriminator.pth")
    all_zero = all(torch.all(v == 0).item() for v in sd.values())
    assert not all_zero, "All discriminator weights are zero — model was not trained"


# ─── 3. Generated Samples Image Validation ───────────────────────────────

def test_generated_samples_is_valid_png():
    """generated_samples.png must be a valid PNG file."""
    path = os.path.join(APP_DIR, "generated_samples.png")
    with open(path, "rb") as f:
        magic = f.read(8)
    assert magic == b'\x89PNG\r\n\x1a\n', "generated_samples.png is not a valid PNG"


def test_generated_samples_minimum_dimensions():
    """generated_samples.png must be at least 112x112 pixels."""
    path = os.path.join(APP_DIR, "generated_samples.png")
    w, h = _read_png_dimensions(path)
    assert w >= 112, f"Image width {w} < 112"
    assert h >= 112, f"Image height {h} < 112"


def test_generated_samples_nonzero_size():
    """generated_samples.png must have non-trivial file size (> 500 bytes)."""
    path = os.path.join(APP_DIR, "generated_samples.png")
    size = os.path.getsize(path)
    assert size > 500, f"generated_samples.png is suspiciously small ({size} bytes)"


# ─── 4. Metrics JSON Validation ──────────────────────────────────────────

def test_metrics_json_is_valid_json():
    """metrics.json must be parseable JSON."""
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    assert data is not None, "metrics.json is not valid JSON"


def test_metrics_has_all_required_keys():
    """metrics.json must contain all six required keys."""
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    required = {
        "num_epochs", "final_g_loss", "final_d_loss",
        "total_training_time_seconds", "num_generated_samples", "device"
    }
    missing = required - set(data.keys())
    assert not missing, f"metrics.json missing keys: {missing}"


def test_metrics_num_epochs():
    """num_epochs must be an integer >= 10."""
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    val = data["num_epochs"]
    assert isinstance(val, int), f"num_epochs should be int, got {type(val).__name__}"
    assert val >= 10, f"num_epochs is {val}, expected >= 10"


def test_metrics_final_g_loss():
    """final_g_loss must be a finite float."""
    import math
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    val = data["final_g_loss"]
    assert isinstance(val, (int, float)), (
        f"final_g_loss should be numeric, got {type(val).__name__}"
    )
    assert math.isfinite(val), f"final_g_loss is not finite: {val}"


def test_metrics_final_d_loss():
    """final_d_loss must be a finite float."""
    import math
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    val = data["final_d_loss"]
    assert isinstance(val, (int, float)), (
        f"final_d_loss should be numeric, got {type(val).__name__}"
    )
    assert math.isfinite(val), f"final_d_loss is not finite: {val}"


def test_metrics_total_training_time():
    """total_training_time_seconds must be a positive number."""
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    val = data["total_training_time_seconds"]
    assert isinstance(val, (int, float)), (
        f"total_training_time_seconds should be numeric, got {type(val).__name__}"
    )
    assert val > 0, f"total_training_time_seconds is {val}, expected > 0"


def test_metrics_num_generated_samples():
    """num_generated_samples must be an integer >= 16."""
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    val = data["num_generated_samples"]
    assert isinstance(val, int), (
        f"num_generated_samples should be int, got {type(val).__name__}"
    )
    assert val >= 16, f"num_generated_samples is {val}, expected >= 16"


def test_metrics_device_is_cpu():
    """device must be the string 'cpu'."""
    data = _load_json(os.path.join(APP_DIR, "metrics.json"))
    val = data["device"]
    assert isinstance(val, str), f"device should be str, got {type(val).__name__}"
    assert val.strip().lower() == "cpu", f"device is '{val}', expected 'cpu'"


# ─── 5. Functional Smoke Test: Generator Forward Pass ────────────────────

def test_generator_forward_pass():
    """
    Load the Generator architecture from train_gan.py, load saved weights,
    and verify a forward pass produces output of shape (1, 784) in [-1, 1].
    """
    import torch
    import importlib.util
    import sys

    script_path = os.path.join(APP_DIR, "train_gan.py")
    if not os.path.isfile(script_path):
        assert False, "train_gan.py not found, cannot run forward pass test"

    # Dynamically import the training script as a module
    spec = importlib.util.spec_from_file_location("train_gan", script_path)
    mod = importlib.util.module_from_spec(spec)

    # Prevent the script from executing main() on import
    original_name = None
    try:
        # We'll exec the module but intercept __name__
        spec.loader.exec_module(mod)
    except SystemExit:
        pass  # Some scripts call sys.exit
    except Exception:
        # If the script runs training on import, skip this test
        import pytest
        pytest.skip("Could not import train_gan.py without side effects")

    # Get the Generator class
    assert hasattr(mod, "Generator"), "train_gan.py has no 'Generator' class"
    gen = mod.Generator()
    sd = torch.load(
        os.path.join(APP_DIR, "generator.pth"),
        map_location="cpu",
        weights_only=True,
    )
    gen.load_state_dict(sd)
    gen.eval()

    with torch.no_grad():
        z = torch.randn(1, 100)
        out = gen(z)

    assert out.shape == (1, 784), f"Generator output shape is {out.shape}, expected (1, 784)"
    assert out.min().item() >= -1.01, f"Generator output min {out.min().item()} < -1.01"
    assert out.max().item() <= 1.01, f"Generator output max {out.max().item()} > 1.01"


def test_discriminator_forward_pass():
    """
    Load the Discriminator from train_gan.py, load saved weights,
    and verify a forward pass produces output of shape (1, 1) in [0, 1].
    """
    import torch
    import importlib.util

    script_path = os.path.join(APP_DIR, "train_gan.py")
    if not os.path.isfile(script_path):
        assert False, "train_gan.py not found"

    spec = importlib.util.spec_from_file_location("train_gan", script_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except (SystemExit, Exception):
        import pytest
        pytest.skip("Could not import train_gan.py without side effects")

    assert hasattr(mod, "Discriminator"), "train_gan.py has no 'Discriminator' class"
    disc = mod.Discriminator()
    sd = torch.load(
        os.path.join(APP_DIR, "discriminator.pth"),
        map_location="cpu",
        weights_only=True,
    )
    disc.load_state_dict(sd)
    disc.eval()

    with torch.no_grad():
        x = torch.randn(1, 784)
        out = disc(x)

    assert out.shape == (1, 1), f"Discriminator output shape is {out.shape}, expected (1, 1)"
    assert out.min().item() >= -0.01, f"Discriminator output < 0 (sigmoid expected)"
    assert out.max().item() <= 1.01, f"Discriminator output > 1 (sigmoid expected)"
