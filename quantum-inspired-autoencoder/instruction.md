## Quantum-Inspired Classical Autoencoder

Implement a quantum-inspired classical autoencoder that emulates a 3-qubit quantum autoencoder (QAE) on the GHZ-state compression task using only classical linear algebra and PyTorch. The autoencoder compresses the 3-qubit GHZ state into a single logical qubit and reconstructs it with high fidelity.

### Technical Requirements

- **Language:** Python 3.x
- **Dependencies:** PyTorch (CPU), NumPy, SciPy, Matplotlib
- **Entry point:** `/app/qae.py` — a single self-contained script that, when executed via `python qae.py`, performs training and produces all required outputs.

### Input State

The 3-qubit GHZ state is defined as:

|ψ⟩ = (|000⟩ + |111⟩) / √2

Represented as a length-8 complex state vector (computational basis ordering: |000⟩, |001⟩, ..., |111⟩).

### Architecture Requirements

1. **Quantum-like gates:** Implement parametrized single-qubit rotation gates R_x(θ), R_y(θ), R_z(θ) and a two-qubit CNOT gate, all operating on the 8-dimensional complex vector space (3-qubit Hilbert space).
2. **Encoder:** Maps the 3-qubit state to a 1-qubit state by tracing out qubits 2 and 3 (partial trace over the last two qubits).
3. **Decoder:** Maps the 1-qubit compressed state back to 3 qubits by tensoring with |0⟩ for qubits 2 and 3, then applying a parametrized decoding circuit.
4. **Gradient estimation:** Use the parameter-shift rule for gradient computation. Do not use autograd/backpropagation through the unitary circuit parameters.
5. **Loss function:** Minimize the infidelity `1 − F(ρ, σ)` where F is the fidelity between the original GHZ state and the reconstructed output state.

### Output Requirements

All output files must be written to `/app/`.

1. **Trained parameters:** Save the trained rotation angles to `/app/ghz_3to1_qae_angles.pt` using `torch.save()`. The saved object must be loadable via `torch.load()` and must be either a 1-D `torch.Tensor` or a dictionary mapping string keys to `torch.Tensor` values.

2. **Reconstructed state:** Save the final reconstructed state vector to `/app/reconstructed_ghz.npy` using `numpy.save()`. The file must contain a 1-D complex NumPy array of length 8 (dtype `complex64` or `complex128`). The vector must be normalized (L2 norm within 1e-4 of 1.0).

3. **Learning curve plot:** Save a plot of infidelity vs. epoch to `/app/learning_curve.png`. The plot must have labeled axes.

4. **Stdout output:** During execution, print the best achieved fidelity to stdout in exactly this format:
   ```
   Best fidelity: <value>
   ```
   where `<value>` is a floating-point number (e.g., `Best fidelity: 0.9213`).

### Performance Requirement

The final compression–decompression fidelity between the original GHZ state and the reconstructed state must be **≥ 0.85**.
