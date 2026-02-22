# xai-method1

**Property-Based XAI for Hardware Trojan Detection**

Ensemble of 31 XGBoost models using circuit property combinations.

---

## Installation

```bash
# Install shared package first
cd ../shared
pip install -e .

# Install method1
cd ../method1-property-based
pip install -e .
```

---

## Pipeline Phases

### Phase 1: Hyperparameter Tuning
```bash
method1-tune --input train.csv --output logs/hyperparameter_tuning_aggregate.json
```

**Files to migrate:**
- `tune_hyperparameters_aggregate.py` -> `tuning/tune.py`

### Phase 2: Model Training
```bash
method1-train --input train.csv --params logs/hyperparameter_tuning_aggregate.json --output models_aggregate/
```

**Files to migrate:**
- `train_property_based_model.py` -> `training/train.py`

### Phase 3: Knowledge Base Processing
```bash
method1-kb --input models_aggregate/ --output kb_output/
```

**Files to migrate:**
- `xai_process_kb.py` -> `kb_processing/process.py`

### Phase 4: Explanation Generation
```bash
method1-explain --input kb_output/ --output explanations_output/
```

**Files to migrate:**
- `xai_build_explanations.js` -> `explanations/build.js`
- Need Node.js wrapper or port to Python

---

## Module Structure

```
method1/
├── tuning/                    # Phase 1: Hyperparameter tuning
│   ├── __init__.py
│   ├── tune.py                # Main tuning logic
│   └── cli.py                 # Command-line interface
│
├── training/                  # Phase 2: Model training
│   ├── __init__.py
│   ├── train.py               # Train 31 SVM models (legacy)
│   ├── train_xgboost.py       # Train 31 XGBoost models (default)
│   └── cli.py
│
├── kb_processing/             # Phase 3: KB processing
│   ├── __init__.py
│   ├── process.py             # Voting weights & ensemble
│   └── cli.py
│
├── explanations/              # Phase 4: Explanation generation
│   ├── __init__.py
│   ├── build.py               # Generate explanations
│   ├── build.js               # Node.js version (legacy)
│   └── cli.py
│
└── tests/                     # Unit tests
    ├── test_tuning.py
    ├── test_training.py
    ├── test_kb.py
    └── test_explanations.py
```

---

## Usage (Python API)

```python
from method1.tuning import tune_hyperparameters
from method1.training import train_models
from method1.kb_processing import process_kb
from method1.explanations import generate_explanations

# Phase 1: Tune
params = tune_hyperparameters(
    train_data="train.csv",
    output_file="logs/tuning.json"
)

# Phase 2: Train
models = train_models(
    train_data="train.csv",
    hyperparameters=params,
    output_dir="models_aggregate/"
)

# Phase 3: KB Processing
kb_data = process_kb(
    models_dir="models_aggregate/",
    output_dir="kb_output/"
)

# Phase 4: Explanations
explanations = generate_explanations(
    kb_dir="kb_output/",
    output_dir="explanations_output/"
)
```

---

## Dependencies

- `xai-shared` - Shared infrastructure
- `xgboost` - XGBoost models (default)
- `scikit-learn` - SVM models (legacy)
- `numpy`, `pandas` - Data handling
- `scipy` - Statistical functions

---

## Node.js Components

Some components use Node.js (explanation generation):

```bash
# Install Node.js dependencies
npm install

# Run explanation generation (legacy)
node method1/explanations/build.js -f kb_output -o explanations_output
```

---

## Testing

```bash
pytest tests/
```

---

## Migration Checklist

- [ ] Migrate `tune_hyperparameters_aggregate.py`
- [ ] Migrate `train_property_based_model.py`
- [ ] Migrate `xai_process_kb.py`
- [ ] Migrate `xai_build_explanations.js` (or port to Python)
- [ ] Create CLI interfaces
- [ ] Write tests
- [ ] Update imports to use `xai_shared`
- [ ] Validate full pipeline
