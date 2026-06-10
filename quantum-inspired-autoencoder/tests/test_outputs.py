"""
Tests for Quantum-Inspired Classical Autoencoder task.

Validates:
1. Output file existence and formats
2. Trained angles file structure (torch.load compatible)
3. Reconstructed state vector properties (shape, dtype, normalization)
4. Fidelity >= 0.85 (independently recomputed against known GHZ state)
5. Learning curve plot validity
"""

import os
import numpy as np
import pytest

# All output files are expected in /app/ per instruction.md
OUTPUT_DIR = "/app"

# The known 3-qubit GHZ state: (|000> + |111>) / sqrt(2)
def get_ghz_state():
    psi = np.zeros(8, dtype=np.complex128)
    psi[0] = 1.0 / np.sqrt(2.0)
    psi[7] = 1.0 / np.sqrt(2.0)
    return psi

def compute_fidelity(psi, phi):
    """Fidelity between two pure state vectors: |<psi|phi>|^2"""
    return float(np.abs(np.vdot(psi, phi)) ** 2)


# ============================================================
# Test 1: Output file existence
# ============================================================

class TestFileExistence:
    def test_angles_file_exists(self):
        path = os.path.join(OUTPUT_DIR, "ghz_3to1_qae_angles.pt")
        assert os.path.isfile(path), (
            f"Trained angles file not found at {path}"
        )

    def test_reconstructed_state_file_exists(self):
        path = os.path.join(OUTPUT_DIR, "reconstructed_ghz.npy")
        assert os.path.isfile(path), (
            f"Reconstructed state file not found at {path}"
        )

    def test_learning_curve_file_exists(self):
        path = os.path.join(OUTPUT_DIR, "learning_curve.png")
        assert os.path.isfile(path), (
            f"Learning curve plot not found at {path}"
        )


# ============================================================
# Test 2: Trained angles file format
# ============================================================

class TestAnglesFile:
    @pytest.fixture
    def angles_path(self):
        return os.path.join(OUTPUT_DIR, "ghz_3to1_qae_angles.pt")

    def test_loadable_with_torch(self, angles_path):
        """File must be loadable via torch.load()."""
        import torch
        if not os.path.isfile(angles_path):
            pytest.skip("Angles file does not exist")
        try:
            data = torch.load(angles_path, map_location="cpu", weights_only=False)
        except Exception as e:
            pytest.fail(f"torch.load() failed: {e}")

    def test_structure_is_tensor_or_dict(self, angles_path):
        """Must be a 1-D Tensor or a dict mapping str -> Tensor."""
        import torch
        if not os.path.isfile(angles_path):
            pytest.skip("Angles file does not exist")
        data = torch.load(angles_path, map_location="cpu", weights_only=False)

        if isinstance(data, torch.Tensor):
            assert data.dim() == 1, (
                f"Expected 1-D tensor, got {data.dim()}-D tensor"
            )
            assert data.numel() > 0, "Tensor is empty (0 elements)"
        elif isinstance(data, dict):
            assert len(data) > 0, "Dictionary is empty"
            for key, val in data.items():
                assert isinstance(key, str), (
                    f"Dict key must be str, got {type(key)}"
                )
                assert isinstance(val, torch.Tensor), (
                    f"Dict value for key '{key}' must be torch.Tensor, "
                    f"got {type(val)}"
                )
        else:
            pytest.fail(
                f"Expected torch.Tensor or dict, got {type(data)}"
            )

    def test_angles_contain_numeric_values(self, angles_path):
        """Angles must contain finite numeric values (not NaN/Inf)."""
        import torch
        if not os.path.isfile(angles_path):
            pytest.skip("Angles file does not exist")
        data = torch.load(angles_path, map_location="cpu", weights_only=False)

        if isinstance(data, torch.Tensor):
            tensors = [data]
        elif isinstance(data, dict):
            tensors = list(data.values())
        else:
            pytest.skip("Unexpected data type")

        for t in tensors:
            assert torch.isfinite(t).all(), (
                "Angle tensor contains NaN or Inf values"
            )

    def test_angles_have_reasonable_count(self, angles_path):
        """
        The autoencoder needs parameters for encoder + decoder circuits.
        There should be a reasonable number of parameters (at least 4).
        """
        import torch
        if not os.path.isfile(angles_path):
            pytest.skip("Angles file does not exist")
        data = torch.load(angles_path, map_location="cpu", weights_only=False)

        total_params = 0
        if isinstance(data, torch.Tensor):
            total_params = data.numel()
        elif isinstance(data, dict):
            total_params = sum(v.numel() for v in data.values())

        assert total_params >= 4, (
            f"Expected at least 4 trainable parameters, got {total_params}. "
            "A quantum-inspired autoencoder needs multiple rotation angles."
        )


# ============================================================
# Test 3: Reconstructed state vector
# ============================================================

class TestReconstructedState:
    @pytest.fixture
    def state_path(self):
        return os.path.join(OUTPUT_DIR, "reconstructed_ghz.npy")

    @pytest.fixture
    def state(self, state_path):
        if not os.path.isfile(state_path):
            pytest.skip("Reconstructed state file does not exist")
        return np.load(state_path)

    def test_is_1d_array(self, state):
        assert state.ndim == 1, (
            f"Expected 1-D array, got {state.ndim}-D array with shape {state.shape}"
        )

    def test_length_is_8(self, state):
        assert state.shape[0] == 8, (
            f"Expected length-8 state vector (3 qubits), got length {state.shape[0]}"
        )

    def test_complex_dtype(self, state):
        assert np.issubdtype(state.dtype, np.complexfloating), (
            f"Expected complex dtype (complex64 or complex128), got {state.dtype}"
        )

    def test_normalization(self, state):
        """L2 norm must be within 1e-4 of 1.0 per instruction."""
        norm = np.linalg.norm(state)
        assert np.isclose(norm, 1.0, atol=1e-4), (
            f"State vector L2 norm is {norm:.6f}, expected ~1.0 (within 1e-4)"
        )

    def test_not_trivial_zero_vector(self, state):
        """State must not be all zeros."""
        assert np.any(np.abs(state) > 1e-10), (
            "State vector is effectively all zeros"
        )

    def test_no_nan_or_inf(self, state):
        """State must not contain NaN or Inf."""
        assert np.all(np.isfinite(state)), (
            "State vector contains NaN or Inf values"
        )


# ============================================================
# Test 4: Fidelity requirement (CORE TEST)
# ============================================================

class TestFidelity:
    @pytest.fixture
    def state_path(self):
        return os.path.join(OUTPUT_DIR, "reconstructed_ghz.npy")

    @pytest.fixture
    def reconstructed(self, state_path):
        if not os.path.isfile(state_path):
            pytest.skip("Reconstructed state file does not exist")
        return np.load(state_path)

    def test_fidelity_at_least_085(self, reconstructed):
        """
        Core requirement: fidelity between reconstructed state and
        the GHZ state must be >= 0.85.
        """
        ghz = get_ghz_state()
        fid = compute_fidelity(ghz, reconstructed)
        assert fid >= 0.85, (
            f"Fidelity is {fid:.4f}, which is below the required threshold of 0.85. "
            f"The autoencoder must compress and reconstruct the GHZ state with F >= 0.85."
        )

    def test_fidelity_is_physically_valid(self, reconstructed):
        """Fidelity must be in [0, 1] range."""
        ghz = get_ghz_state()
        fid = compute_fidelity(ghz, reconstructed)
        assert 0.0 <= fid <= 1.0 + 1e-6, (
            f"Fidelity is {fid:.6f}, which is outside the valid [0, 1] range"
        )

    def test_state_is_not_trivially_ghz_basis_state(self, reconstructed):
        """
        Verify the state is not just |000> or |111> (which would give F=0.5).
        A proper reconstruction should have significant overlap with both
        computational basis states of the GHZ state.
        """
        amp_000 = np.abs(reconstructed[0])
        amp_111 = np.abs(reconstructed[7])
        # Both amplitudes should be non-negligible for a good GHZ reconstruction
        assert amp_000 > 0.1, (
            f"|000> amplitude is {amp_000:.4f}, too small for a GHZ reconstruction"
        )
        assert amp_111 > 0.1, (
            f"|111> amplitude is {amp_111:.4f}, too small for a GHZ reconstruction"
        )


# ============================================================
# Test 5: Learning curve plot
# ============================================================

class TestLearningCurve:
    @pytest.fixture
    def plot_path(self):
        return os.path.join(OUTPUT_DIR, "learning_curve.png")

    def test_file_is_valid_png(self, plot_path):
        """File must be a valid PNG image."""
        if not os.path.isfile(plot_path):
            pytest.skip("Learning curve file does not exist")
        # Check PNG magic bytes
        with open(plot_path, "rb") as f:
            header = f.read(8)
        png_signature = b'\x89PNG\r\n\x1a\n'
        assert header == png_signature, (
            "learning_curve.png does not have a valid PNG header"
        )

    def test_file_is_not_empty(self, plot_path):
        """Plot file must have meaningful content (not just a header)."""
        if not os.path.isfile(plot_path):
            pytest.skip("Learning curve file does not exist")
        size = os.path.getsize(plot_path)
        # A matplotlib plot with axes should be at least a few KB
        assert size > 1000, (
            f"learning_curve.png is only {size} bytes, "
            "expected a meaningful plot (> 1KB)"
        )

    def test_image_is_loadable(self, plot_path):
        """Image must be loadable by PIL/Pillow."""
        if not os.path.isfile(plot_path):
            pytest.skip("Learning curve file does not exist")
        try:
            from PIL import Image
            img = Image.open(plot_path)
            img.verify()
        except ImportError:
            pytest.skip("Pillow not available for image verification")
        except Exception as e:
            pytest.fail(f"Failed to load learning_curve.png as image: {e}")


# ============================================================
# Test 6: GHZ state properties of reconstructed output
# ============================================================

class TestGHZProperties:
    """
    Additional physics-based checks to ensure the reconstructed state
    has properties consistent with a GHZ-like state.
    """

    @pytest.fixture
    def reconstructed(self):
        path = os.path.join(OUTPUT_DIR, "reconstructed_ghz.npy")
        if not os.path.isfile(path):
            pytest.skip("Reconstructed state file does not exist")
        return np.load(path)

    def test_dominant_amplitudes_on_000_and_111(self, reconstructed):
        """
        For a good GHZ reconstruction, the dominant amplitudes should be
        on |000> (index 0) and |111> (index 7). The sum of their squared
        magnitudes should be significantly larger than the rest.
        """
        probs = np.abs(reconstructed) ** 2
        ghz_prob = probs[0] + probs[7]
        # With fidelity >= 0.85, the GHZ components should dominate
        assert ghz_prob > 0.70, (
            f"Combined probability on |000> and |111> is {ghz_prob:.4f}, "
            f"expected > 0.70 for a good GHZ reconstruction"
        )

    def test_relative_phase_approximately_correct(self, reconstructed):
        """
        In the ideal GHZ state, |000> and |111> have the same phase.
        For a good reconstruction, the relative phase should be close to 0
        (or equivalently, the amplitudes should have similar phase).
        We allow generous tolerance since fidelity >= 0.85 is the hard requirement.
        """
        amp_000 = reconstructed[0]
        amp_111 = reconstructed[7]

        if np.abs(amp_000) < 0.1 or np.abs(amp_111) < 0.1:
            pytest.skip("Amplitudes too small for phase comparison")

        # Relative phase between the two dominant components
        relative_phase = np.angle(amp_111) - np.angle(amp_000)
        # Normalize to [-pi, pi]
        relative_phase = (relative_phase + np.pi) % (2 * np.pi) - np.pi
        # Allow generous tolerance (within ~60 degrees)
        assert np.abs(relative_phase) < 1.1, (
            f"Relative phase between |000> and |111> is {np.degrees(relative_phase):.1f}°, "
            f"expected close to 0° for GHZ state reconstruction"
        )
