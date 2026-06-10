## RSA Key Recovery from Faulty Encryption Oracle

Exploit a faulty RSA encryption oracle to recover the private key and decrypt a target ciphertext.

### Technical Requirements

- Language: Python 3
- Input file: `/app/input.json`
- Output file: `/app/output.json`
- You may use standard libraries and `pycryptodome` (or `pycrypto`).

### Input Specification

`/app/input.json` contains a JSON object with the following fields:

- `n` (string): RSA modulus N in decimal.
- `e` (integer): RSA public exponent.
- `ciphertext` (string): The target ciphertext to decrypt, as a decimal integer string.
- `faulty_pairs` (array of objects): A list of oracle observations. Each object has:
  - `message` (string): The plaintext message m sent to the oracle, as a decimal integer string.
  - `correct_ciphertext` (string): The correct encryption c = m^e mod N, as a decimal integer string.
  - `faulty_ciphertext` (string): The faulty encryption c' produced by the oracle, as a decimal integer string.

The fault model: the oracle uses CRT-based RSA. During computation, one of the two partial exponentiations (mod p or mod q) is occasionally corrupted, producing a faulty result. Specifically, for a faulty ciphertext c', either:
- `c' ≡ m^e (mod p)` but `c' ≢ m^e (mod q)`, or
- `c' ≡ m^e (mod q)` but `c' ≢ m^e (mod p)`

This means `gcd(c' - c, N)` reveals one of the prime factors p or q, where c is the correct ciphertext.

### Output Specification

Write `/app/output.json` as a JSON object with the following fields:

- `p` (string): One prime factor of N, as a decimal integer string.
- `q` (string): The other prime factor of N, as a decimal integer string. Must satisfy `p * q == N`.
- `d` (string): The RSA private exponent, as a decimal integer string. Must satisfy `e * d ≡ 1 (mod lcm(p-1, q-1))`.
- `plaintext` (string): The decrypted target ciphertext, as a decimal integer string. Must satisfy `plaintext == ciphertext^d mod N`.

### Constraints

- All integer values in input and output are represented as decimal strings (except `e` which is an integer).
- The `faulty_pairs` array contains at least one pair where the fault leaks a factor of N.
- The recovered `p` and `q` must be prime and their product must equal `N`.
- The decrypted `plaintext` must be correct with respect to standard RSA decryption.

### Solution Script

Name your solution `solve.py` in `/app/`. It should read `/app/input.json` and write `/app/output.json`.
