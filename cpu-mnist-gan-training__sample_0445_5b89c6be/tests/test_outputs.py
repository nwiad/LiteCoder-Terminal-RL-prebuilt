"""
Tests for CPU-Based MNIST GAN Training Task.

Validates:
- Required file existence and structure
- Model architecture (Generator/Discriminator I/O shapes)
- Checkpoint loadability and compatibility
- Training log JSON schema and content
- Generated image validity (PNG format)
- CPU-only constraint (no CUDA usage in source)
- Loss value sanity (positive, finite)
"""

import os
import sys
import json
import struct

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = "/app/mnist_gan"
MODEL_PY = os.path.join(BASE_DIR, "model.py")
TRAIN_PY = os.path.join(BASE_DIR, "train.py")
SAMPLE_PY = os.path.join(BASE_DIR, "sample.py")
REQUIREMENTS = os.path.join(BASE_DIR, "requirements.txt")
TRAINING_LOG = os.path.join(BASE_DIR, "training_log.json")
CHECKPOINT = os.path.join(BASE_DIR, "checkpoints", "generator_final.pt")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
GENERATED_SAMPLES = os.path.join(OUTPUTS_DIR, "generated_samples.png")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_valid_png(filepath):
    """Check if a file starts with the PNG magic bytes."""
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
        return header == PNG_MAGIC
    except Exception:
        return False


def _file_exists_and_nonempty(filepath):
    return os.path.isfile(filepath) and os.path.getsize(filepath) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """All required project files must exist and be non-empty."""

    def test_model_py_exists(self):
        assert _file_exists_and_nonempty(MODEL_PY), f"model.py missing or empty at {MODEL_PY}"

    def test_train_py_exists(self):
        assert _file_exists_and_nonempty(TRAIN_PY), f"train.py missing or empty at {TRAIN_PY}"

    def test_sample_py_exists(self):
        assert _file_exists_and_nonempty(SAMPLE_PY), f"sample.py missing or empty at {SAMPLE_PY}"

    def test_requirements_txt_exists(self):
        assert _file_exists_and_nonempty(REQUIREMENTS), f"requirements.txt missing or empty at {REQUIREMENTS}"

    def test_training_log_exists(self):
        assert _file_exists_and_nonempty(TRAINING_LOG), f"training_log.json missing or empty at {TRAINING_LOG}"

    def test_checkpoint_exists(self):
        assert _file_exists_and_nonempty(CHECKPOINT), f"generator_final.pt missing or empty at {CHECKPOINT}"

    def test_generated_samples_exists(self):
        assert _file_exists_and_nonempty(GENERATED_SAMPLES), (
            f"generated_samples.png missing or empty at {GENERATED_SAMPLES}"
        )

    def test_epoch_images_exist(self):
        """At least epoch_1.png through epoch_5.png must exist."""
        for i in range(1, 6):
            path = os.path.join(OUTPUTS_DIR, f"epoch_{i}.png")
            assert os.path.isfile(path), f"Missing epoch image: {path}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. TRAINING LOG VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

class TestTrainingLog:
    """training_log.json must be valid JSON with correct schema."""

    def _load_log(self):
        with open(TRAINING_LOG, "r") as f:
            return json.load(f)

    def test_valid_json(self):
        """File must be parseable JSON."""
        try:
            self._load_log()
        except (json.JSONDecodeError, Exception) as e:
            assert False, f"training_log.json is not valid JSON: {e}"

    def test_has_epochs_key(self):
        data = self._load_log()
        assert "epochs" in data, "training_log.json must contain an 'epochs' key"
        assert isinstance(data["epochs"], list), "'epochs' must be a list"

    def test_at_least_5_epochs(self):
        data = self._load_log()
        epochs = data["epochs"]
        assert len(epochs) >= 5, f"Expected at least 5 epoch entries, got {len(epochs)}"

    def test_epoch_entry_schema(self):
        """Each epoch entry must have epoch (int), d_loss (float), g_loss (float)."""
        data = self._load_log()
        for i, entry in enumerate(data["epochs"]):
            assert "epoch" in entry, f"Entry {i} missing 'epoch' field"
            assert "d_loss" in entry, f"Entry {i} missing 'd_loss' field"
            assert "g_loss" in entry, f"Entry {i} missing 'g_loss' field"

            assert isinstance(entry["epoch"], int), (
                f"Entry {i}: 'epoch' must be int, got {type(entry['epoch']).__name__}"
            )
            assert isinstance(entry["d_loss"], (int, float)), (
                f"Entry {i}: 'd_loss' must be numeric, got {type(entry['d_loss']).__name__}"
            )
            assert isinstance(entry["g_loss"], (int, float)), (
                f"Entry {i}: 'g_loss' must be numeric, got {type(entry['g_loss']).__name__}"
            )

    def test_epoch_numbers_sequential(self):
        """Epoch numbers should be sequential starting from 1."""
        data = self._load_log()
        epoch_nums = [e["epoch"] for e in data["epochs"]]
        expected = list(range(1, len(epoch_nums) + 1))
        assert epoch_nums == expected, (
            f"Epoch numbers should be sequential from 1, got {epoch_nums}"
        )

    def test_losses_are_finite_and_positive(self):
        """Losses must be finite positive numbers (not NaN, Inf, or negative)."""
        import math
        data = self._load_log()
        for entry in data["epochs"]:
            d = entry["d_loss"]
            g = entry["g_loss"]
            assert math.isfinite(d) and d >= 0, (
                f"Epoch {entry['epoch']}: d_loss={d} is not a valid non-negative finite number"
            )
            assert math.isfinite(g) and g >= 0, (
                f"Epoch {entry['epoch']}: g_loss={g} is not a valid non-negative finite number"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 3. IMAGE VALIDITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestImageValidity:
    """All output PNGs must be valid PNG files with reasonable size."""

    def test_epoch_images_are_valid_png(self):
        for i in range(1, 6):
            path = os.path.join(OUTPUTS_DIR, f"epoch_{i}.png")
            assert _is_valid_png(path), f"{path} is not a valid PNG file"

    def test_generated_samples_is_valid_png(self):
        assert _is_valid_png(GENERATED_SAMPLES), (
            f"{GENERATED_SAMPLES} is not a valid PNG file"
        )

    def test_epoch_images_have_reasonable_size(self):
        """Each epoch image should be at least 1KB (not a trivially small file)."""
        for i in range(1, 6):
            path = os.path.join(OUTPUTS_DIR, f"epoch_{i}.png")
            size = os.path.getsize(path)
            assert size > 1024, (
                f"{path} is suspiciously small ({size} bytes), expected > 1KB for a 64-image grid"
            )

    def test_generated_samples_has_reasonable_size(self):
        size = os.path.getsize(GENERATED_SAMPLES)
        assert size > 1024, (
            f"generated_samples.png is suspiciously small ({size} bytes)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 4. MODEL ARCHITECTURE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestModelArchitecture:
    """Generator and Discriminator must have correct I/O tensor shapes."""

    def _import_model(self):
        """Import model.py from the project directory."""
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        # Force reimport in case of caching issues
        if "model" in sys.modules:
            del sys.modules["model"]
        import model
        return model

    def test_generator_class_exists(self):
        model = self._import_model()
        assert hasattr(model, "Generator"), "model.py must define a 'Generator' class"

    def test_discriminator_class_exists(self):
        model = self._import_model()
        assert hasattr(model, "Discriminator"), "model.py must define a 'Discriminator' class"

    def test_generator_constructor_accepts_latent_dim(self):
        """Generator(latent_dim=100) must work."""
        model = self._import_model()
        import torch
        try:
            gen = model.Generator(latent_dim=100)
        except Exception as e:
            assert False, f"Generator(latent_dim=100) raised: {e}"

    def test_generator_output_shape(self):
        """Generator must map (N, 100) -> (N, 1, 28, 28)."""
        model = self._import_model()
        import torch
        gen = model.Generator(latent_dim=100)
        gen.eval()
        z = torch.randn(4, 100)
        with torch.no_grad():
            out = gen(z)
        assert out.shape == (4, 1, 28, 28), (
            f"Generator output shape should be (4, 1, 28, 28), got {tuple(out.shape)}"
        )

    def test_generator_output_range(self):
        """Generator output should be in [-1, 1] (Tanh activation)."""
        model = self._import_model()
        import torch
        gen = model.Generator(latent_dim=100)
        gen.eval()
        z = torch.randn(8, 100)
        with torch.no_grad():
            out = gen(z)
        assert out.min() >= -1.0 - 1e-6, f"Generator output min {out.min()} < -1"
        assert out.max() <= 1.0 + 1e-6, f"Generator output max {out.max()} > 1"

    def test_discriminator_output_shape(self):
        """Discriminator must map (N, 1, 28, 28) -> (N, 1)."""
        model = self._import_model()
        import torch
        disc = model.Discriminator()
        disc.eval()
        x = torch.randn(4, 1, 28, 28)
        with torch.no_grad():
            out = disc(x)
        assert out.shape == (4, 1), (
            f"Discriminator output shape should be (4, 1), got {tuple(out.shape)}"
        )

    def test_discriminator_output_range(self):
        """Discriminator output should be in [0, 1] (Sigmoid activation)."""
        model = self._import_model()
        import torch
        disc = model.Discriminator()
        disc.eval()
        x = torch.randn(8, 1, 28, 28)
        with torch.no_grad():
            out = disc(x)
        assert out.min() >= 0.0 - 1e-6, f"Discriminator output min {out.min()} < 0"
        assert out.max() <= 1.0 + 1e-6, f"Discriminator output max {out.max()} > 1"

    def test_generator_batch_size_flexibility(self):
        """Generator should work with different batch sizes."""
        model = self._import_model()
        import torch
        gen = model.Generator(latent_dim=100)
        gen.eval()
        for bs in [1, 16, 64]:
            z = torch.randn(bs, 100)
            with torch.no_grad():
                out = gen(z)
            assert out.shape == (bs, 1, 28, 28), (
                f"Generator failed for batch_size={bs}: got shape {tuple(out.shape)}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 5. CHECKPOINT VALIDITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckpoint:
    """generator_final.pt must be a valid state dict loadable into Generator(100)."""

    def _import_model(self):
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        if "model" in sys.modules:
            del sys.modules["model"]
        import model
        return model

    def test_checkpoint_is_loadable(self):
        """Checkpoint must be loadable via torch.load."""
        import torch
        try:
            state_dict = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        except Exception as e:
            assert False, f"Failed to load checkpoint: {e}"
        assert isinstance(state_dict, dict), (
            f"Checkpoint should be a dict (state_dict), got {type(state_dict).__name__}"
        )

    def test_checkpoint_compatible_with_generator(self):
        """State dict must load into Generator(latent_dim=100) without errors."""
        import torch
        model = self._import_model()
        gen = model.Generator(latent_dim=100)
        state_dict = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        try:
            gen.load_state_dict(state_dict)
        except Exception as e:
            assert False, (
                f"Checkpoint state dict is incompatible with Generator(100): {e}"
            )

    def test_loaded_generator_produces_valid_output(self):
        """Generator loaded from checkpoint must produce correct output shape."""
        import torch
        model = self._import_model()
        gen = model.Generator(latent_dim=100)
        state_dict = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        gen.load_state_dict(state_dict)
        gen.eval()
        z = torch.randn(4, 100)
        with torch.no_grad():
            out = gen(z)
        assert out.shape == (4, 1, 28, 28), (
            f"Loaded generator output shape: {tuple(out.shape)}, expected (4, 1, 28, 28)"
        )

    def test_checkpoint_has_trained_weights(self):
        """Checkpoint weights should differ from a freshly initialized Generator.
        This catches the case where someone saves an untrained model."""
        import torch
        model = self._import_model()

        # Load checkpoint
        gen_loaded = model.Generator(latent_dim=100)
        state_dict = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        gen_loaded.load_state_dict(state_dict)

        # Create fresh model with fixed seed for comparison
        torch.manual_seed(42)
        gen_fresh = model.Generator(latent_dim=100)

        # Compare: at least some parameters should differ
        any_different = False
        for (name, p_loaded), (_, p_fresh) in zip(
            gen_loaded.named_parameters(), gen_fresh.named_parameters()
        ):
            if not torch.equal(p_loaded, p_fresh):
                any_different = True
                break

        assert any_different, (
            "Checkpoint weights appear identical to a freshly initialized model — "
            "training may not have occurred"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 6. CPU-ONLY CONSTRAINT
# ══════════════════════════════════════════════════════════════════════════════

class TestCPUOnly:
    """Source files must not use CUDA."""

    def _read_source(self, filepath):
        with open(filepath, "r") as f:
            return f.read()

    def test_model_no_cuda(self):
        """model.py should not contain active CUDA usage."""
        src = self._read_source(MODEL_PY)
        # Strip comments before checking
        lines = [l for l in src.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(lines)
        assert ".cuda()" not in code, "model.py uses .cuda() — must be CPU only"
        assert '.to("cuda")' not in code and ".to('cuda')" not in code, (
            "model.py uses .to('cuda') — must be CPU only"
        )

    def test_train_no_cuda_device(self):
        """train.py should not use .to('cuda') or torch.device('cuda')."""
        src = self._read_source(TRAIN_PY)
        # Allow comments mentioning cuda, but not actual usage
        lines = [l for l in src.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(lines)
        assert '.to("cuda")' not in code and ".to('cuda')" not in code, (
            "train.py uses .to('cuda') — must be CPU only"
        )
        assert 'device("cuda")' not in code and "device('cuda')" not in code, (
            "train.py uses torch.device('cuda') — must be CPU only"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 7. REQUIREMENTS.TXT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

class TestRequirements:
    """requirements.txt must list torch as a dependency."""

    def test_torch_in_requirements(self):
        with open(REQUIREMENTS, "r") as f:
            content = f.read().lower()
        assert "torch" in content, (
            "requirements.txt must include 'torch' as a dependency"
        )

