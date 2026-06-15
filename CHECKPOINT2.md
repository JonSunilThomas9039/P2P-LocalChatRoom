# Checkpoint 2: Stream Framing & End-to-End Encryption

This phase introduces cryptographic key negotiation, AES authenticated block encryption, and custom stream framing to eliminate socket data smearing.

## 🏗️ Technical Component Overview

### 1. Dynamic Diffie-Hellman Handshake
To negotiate a secret key over an open connection without pre-sharing data, a dynamic tie-breaker engine was implemented:
* Both nodes generate a random integer `r`.
* The node with the higher integer becomes the primary parameter generator. It selects a safe prime $p$ using `sympy.randprime(10000, 10000000)`, a base generator $g$, and a private integer $b$.
* It calculates its public key via modular exponentiation: 

    $$B = g^b \pmod p$$

    and transmits $(p, g, B)$ to the follower.
* The follower computes its public key:

    $$A = g^a \pmod p$$

    and returns it.
* Both nodes calculate the shared key:

    $$K = A^b \pmod p = B^a \pmod p$$

* This shared integer is hashed via SHA-256 to generate a consistent 256-bit key for symmetric encryption.

### 2. Symmetrical Encryption Space (AES-GCM)
Plaintext is encrypted using Advanced Encryption Standard in Galois/Counter Mode (AES-GCM). Every message generates a completely random 12-byte initialization vector (nonce). The nonce is appended to the ciphertext data stream and decrypted on the receiving end.

---

## ⚠️ Stream Engineering & Encryption Pitfalls Faced

### 1. TCP Byte Stream Fragmentation (The "Data Smearing" Problem)
* **The Problem:** Right after the readiness check passed, the handshake process crashed with a `ValueError: invalid literal for int() with base 10: 'Ready from my side'`.
* **The Cause:** TCP is inherently a continuous streaming protocol, not a discrete message protocol. It has no concept of where one `.send()` command ends and another begins. Because the readiness text string and the initial handshake integers were sent rapidly, the operating system's kernel packed them into the same network frame. The receiver's `.recv(4096)` swallowed the entire combined block at once, corrupting the numbers with text data.
* **The Resolution:** Designed a custom framing layer called **Delimiter-Based Framing**. Created a specialized processing function (`chunkify()`) that reads data byte-by-byte (`recv(1)`) and buffers content sequentially, releasing data to the main application only when encountering a trailing newline delimiter (`\n`).

### 2. Asymmetric Pipeline Hangs (Missing Handshake Delimiter)
* **The Problem:** The handshake routine frequently froze halfway through execution, locking up both terminal threads.
* **The Cause:** While the system was successfully upgraded to handle custom delimiter loops via `chunkify()`, one of the internal public key math transmissions (`alice`) was sent across the wire as a raw string lacking the trailing `\n`. The peer node sat blocking indefinitely on the socket waiting for a newline token that never came.
* **The Resolution:** Adjusted all handshake equations to guarantee string transmissions append explicit trailing delimiters (`\n`).

### 3. Encrypted Ciphertext Buffer Deflection
* **The Problem:** The key exchange completed successfully, but the moment a chat message was typed, the receiver thread crashed with `TypeError: Cannot convert "<class 'str'>" instance to a buffer`.
* **The Cause:** `chunkify()` relies on text parsing (`.decode("utf-8")`) to catch newlines. However, encrypted cryptographic blocks (`nonce` + `cipher`) consist of raw binary bytes that cannot be safely converted to UTF-8 text strings without corrupting the cryptographic structure. Additionally, random ciphertext bytes can occasionally evaluate to `0x0A` (the ASCII value for `\n`), causing the delimiter function to stop reading prematurely.
* **The Resolution:** Switched the application to a hybrid protocol network flow:
    * *Phase 1 (Handshake):* Uses string-delimited parsing (`chunkify()`) to exchange text configurations cleanly.
    * *Phase 2 (Active Chat):* Drops delimiter tracking entirely and switches to raw binary streaming (`.recv(4096)`) since each cryptographic payload is handled as an independent, self-contained binary packet.

### 4. Console Concurrency & Input Redundancy
* **The Problem:** Concurrent asynchronous terminal output and active input collection caused text loops to collide on screen. Typing an input phrase caused the system to print redundant string lines, breaking terminal readability.
* **The Cause:** The text tracking inputs and background string collectors were constantly fighting for control of the stdout display interface simultaneously.
* **The Resolution:** Cleaned up local display outputs and injected a raw ANSI Escape Sequence string (`\033[A\033[K`) right after string capture. This instantly pushes the cursor up a line and wipes out the user's typed input text the moment they hit enter. This leaves all message presentation tasks strictly to the background decryption engine, keeping the screen clean.