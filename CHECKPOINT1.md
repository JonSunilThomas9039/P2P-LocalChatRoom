# Checkpoint 1: Asynchronous Duplex Infrastructure

This milestone establishes the underlying P2P mesh network, allowing two systems to execute concurrent read/write actions simultaneously.

## 🏗️ Architectural Design
Standard chat programs use a Server-Client layout where a central server passes messages between clients. This checkpoint bypasses that by forcing each instance of the script to behave as **both a server and a client at the same time**.

When the application boots:
1.  An **Inbound Server Thread** initializes `socket.bind()` on the local user's assigned port and calls `.accept()`, blocking until a peer dials in.
2.  An **Outbound Client Thread** concurrently loops a `socket.connect()` call targeting the other peer's listening port layout.

This forms a cross-connected, duplex data pipeline across our local mapping coordinates:
* **Jon:** Listens on port `50000` | Dials port `51000`
* **Jom:** Listens on port `51000` | Dials port `50000`

---

## ⚠️ Network & Multi-Threading Challenges Faced

During development, several critical socket crashes and thread failures were encountered and resolved:

### 1. The Thread Positional Parameter Crash
* **The Problem:** The script crashed on initialization with `AssertionError: group argument must be None for now`.
* **The Cause:** In Python's `threading.Thread` initialization, the first positional argument is reserved for an unimplemented internal parameter (`group`). Dropping the callback function directly into the constructor passed it into the wrong parameter space.
* **The Resolution:** Explicitly redefined the thread assignments using keyword targets (`target=create_Client, args=(...)`).

### 2. Slicing/Variable Resolution Failures
* **The Problem:** The client connecting thread spun endlessly in an exception-catching loop, failing to reach the peer socket.
* **The Cause:** The target name string (`"Jom"`) was passed into the socket initialization engine instead of passing the network configuration details. The socket logic attempted to slice the string variable (`user[0]` and `user[1]`), meaning it was literally trying to dial an IP address of `"J"` on a port of `"o"`.
* **The Resolution:** Changed the parameters so that the main initialization sequence performs a precise dictionary lookup (`users[user]`) before feeding network data to the background worker.

### 3. Application-Layer Race Conditions (The "Connected vs. Ready" Trap)
* **The Problem:** Nodes ran side-by-side frequently tripped over immediate crashes: `OSError: [Errno 107] Transport endpoint is not connected` or `BrokenPipeError: [Errno 32] Broken pipe`.
* **The Cause:** The script relied on a local check (`while client1 is None or client2 is None:`) to verify connections. The microsecond the operating system kernel finished the TCP 3-way handshake, the local variables filled up and the script immediately sent data. However, the *remote* computer's Python application layer was a few CPU cycles behind its kernel and hadn't yet returned the fully formed socket object from `accept()`. Data arrived at an uninitialized application door, collapsing the pipe.
* **The Resolution:** Implemented a mandatory application-layer synchronization gate. Both nodes are now forced to exchange explicit state updates and confirm they are listening before any handshake math can proceed.

3. CHECKPOINT2.md

This file outlines the implementation of your cryptography pipeline and stream framing layout.
Markdown