# xai-data-acquisition

**Trust-Hub Circuit Downloader**

Downloads hardware trojan benchmarks from Trust-Hub website.

This is a Python wrapper around the existing `dl_trust_hub` repository which has Rust and Node.js implementations.

---

## Installation

```bash
pip install -e .

# For Node.js version
npm install

# For Rust version
cargo build --release
```

---

## Usage

### Python API
```python
from data_acquisition import download_circuits

# Download all circuits
download_circuits(output_dir="data/raw/")

# Download specific circuits
download_circuits(
    circuits=["s27", "s38584"],
    output_dir="data/raw/"
)
```

### Command Line
```bash
# Download all circuits
xai-download --output data/raw/

# Download specific circuits
xai-download --circuits s27 s38584 --output data/raw/
```

### Node.js Version (Legacy)
```bash
npm install
mkdir data
node index.js
```

### Rust Version (Legacy)
```bash
mkdir data
cargo run
```

---

## Integration with dl_trust_hub

This package wraps the existing `dl_trust_hub` repository:

**Original location:** See the `dl_trust_hub` repository (external dependency)

**Migration strategy:**
1. Keep `dl_trust_hub` as separate git submodule
2. Python wrapper calls Node.js or Rust implementation
3. Or: Reimplement downloader in pure Python

---

## Structure

```
data_acquisition/
├── downloader/
│   ├── __init__.py
│   ├── download.py         # Python implementation
│   ├── wrapper.py          # Wrapper for Rust/Node.js
│   └── cli.py              # Command-line interface
│
└── tests/
    └── test_downloader.py
```

---

## Files from dl_trust_hub

**To migrate or wrap:**
- `index.js` - Node.js downloader
- `src/main.rs` - Rust downloader
- `Cargo.toml` - Rust config
- `package.json` - Node.js config

**Decision needed:**
- Keep as submodule + Python wrapper?
- Port to pure Python?
- Maintain multiple implementations?

---

## Git Submodule Strategy

```bash
# In main repo
git submodule add <dl_trust_hub_url> packages/data-acquisition/dl_trust_hub

# Python wrapper calls:
cd packages/data-acquisition/dl_trust_hub
node index.js  # or: cargo run
```

---

## Testing

```bash
pytest tests/
```

---

## Migration Checklist

- [ ] Decide: Submodule vs pure Python port
- [ ] If submodule: Add dl_trust_hub as submodule
- [ ] If pure Python: Reimplement downloader
- [ ] Create Python wrapper/API
- [ ] Create CLI interface
- [ ] Write tests
- [ ] Document Trust-Hub URL structure
