# Molecular Docking Guide

A complete guide to the molecular docking feature in the AI Drug Discovery Platform.

---

## What is Molecular Docking?

Molecular docking is a computational simulation that predicts how a small molecule (drug candidate) fits into a protein's binding site. Think of it like finding the right key for a lock — the drug is the key, and the protein is the lock.

**Why it matters**: If a drug binds strongly to a disease-related protein, it may effectively block or modify that protein's function, potentially treating the disease.

---

## Docking Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Input     │───▶│  Prepare    │───▶│  Define     │───▶│  Run Vina   │───▶│   Parse     │
│  Candidate  │    │  Structures │    │  Grid Box   │    │  Docking    │    │  Results    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     │                   │                   │                   │                   │
     ▼                   ▼                   ▼                   ▼                   ▼
  CHEMBL ID         PDB → PDBQT         Center on           9 poses            Binding
  + SMILES          SMILES → 3D         binding site        generated          affinity
  + Target                                                                      + RMSD
```

---

## Step-by-Step Process

### Step 1: Input Selection

**What happens**: User selects a drug candidate to dock against its target protein.

**Example from your results**:
- Candidate: **ORE-1001** (CHEMBL429844)
- Target: Protein associated with COVID-19
- Input format: SMILES string (molecular structure as text)

---

### Step 2: Structure Preparation

**Tools used**:

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| **OpenBabel** | Convert molecule formats | SMILES string | 3D structure (PDBQT) |
| **Meeko** | Prepare ligand for docking | 3D structure | Docking-ready PDBQT |
| **AlphaFold** | Fetch protein structure | UniProt ID | PDB file |

**What happens**:

1. **Ligand preparation** (drug molecule):
   - SMILES → 3D coordinates (OpenBabel generates 3D geometry)
   - Add hydrogens and partial charges
   - Convert to PDBQT format (required by AutoDock Vina)

2. **Receptor preparation** (target protein):
   - Fetch PDB structure from AlphaFold
   - Remove water molecules
   - Add polar hydrogens
   - Convert to PDBQT format

---

### Step 3: Grid Box Definition

**What happens**: Define the search space where Vina will look for binding poses.

**Parameters**:
- **Center**: X, Y, Z coordinates of the binding site
- **Size**: Box dimensions (typically 20-30 Ångströms)
- **Spacing**: Grid point spacing (default: 0.375 Å)

**How it's calculated**: 
- If known binding site exists: Center on that site
- Otherwise: Auto-detect pockets or use protein center

---

### Step 4: AutoDock Vina Execution

**Tool**: AutoDock Vina (open-source molecular docking software)

**What it does**:
1. Places the drug molecule in random orientations within the grid box
2. Calculates the binding energy for each orientation
3. Optimizes poses using gradient descent
4. Scores each pose based on:
   - Van der Waals interactions
   - Hydrogen bonds
   - Electrostatic interactions
   - Desolvation effects
   - Torsional entropy

**Output**: Multiple binding poses ranked by binding affinity (kcal/mol)

**Time**: 5-30 minutes depending on molecule flexibility

---

### Step 5: Results Parsing

**What's extracted from Vina output**:

| Metric | Description | Your Example |
|--------|-------------|--------------|
| **Binding Affinity** | Energy score (kcal/mol) | -6.52 kcal/mol |
| **Pose Count** | Number of binding modes found | 9 poses |
| **RMSD (Lower Bound)** | Minimum structural deviation from best pose | 0.000 - 26.640 Å |
| **RMSD (Upper Bound)** | Maximum structural deviation from best pose | 0.000 - 28.540 Å |

---

## Understanding Your Results

### Binding Affinity Interpretation

| Range | Quality | Meaning |
|-------|---------|---------|
| **≤ -9 kcal/mol** | Excellent | Very strong binding, high potential |
| **-9 to -7 kcal/mol** | Good | Strong binding, promising candidate |
| **-7 to -5 kcal/mol** | Moderate | Decent binding, worth investigating |
| **> -5 kcal/mol** | Weak | Poor binding, likely ineffective |

**Your best result**: **-6.52 kcal/mol** = **Moderate** binding

This means ORE-1001 shows reasonable interaction with the COVID-19 target, but isn't a strong binder.

---

### Pose Analysis (Your 9 Poses)

| Rank | Affinity | Quality | RMSD (LB) | Interpretation |
|------|----------|---------|-----------|----------------|
| #1 | -6.52 | Moderate | 0.000 Å | **Best pose** - reference point |
| #2 | -6.51 | Moderate | 0.324 Å | Very similar to best (consistent) |
| #3 | -5.13 | Moderate | 1.902 Å | Similar binding mode |
| #4 | -4.86 | Weak | 1.653 Å | Similar but weaker |
| #5 | -1.80 | Weak | 26.640 Å | **Different binding site** |
| #6-9 | Positive | Weak | >14 Å | Unfavorable binding |

**Key observations**:
- Poses 1-4 cluster together (low RMSD) = consistent binding mode
- Poses 5-9 have high RMSD = binding at different locations
- Positive affinities (poses 6-9) = unfavorable, repulsive interactions

---

### RMSD Explained

**RMSD (Root Mean Square Deviation)** measures how different two poses are structurally.

```
Low RMSD (<2 Å)  → Poses are very similar (same binding mode)
High RMSD (>5 Å) → Poses are different (different binding site or orientation)
```

**RMSD Lower Bound (LB)**: Minimum deviation (best-case alignment)
**RMSD Upper Bound (UB)**: Maximum deviation (worst-case alignment)

**In your results**:
- Poses 1-4: RMSD LB < 2 Å → All bind the same way
- Poses 5-9: RMSD LB > 14 Å → Different binding locations (likely artifacts)

---

### Score Update Mechanism

**Original Score**: 0.9 (from discovery pipeline)
**Updated Score**: 2.3 (+1.4)

**Formula**:
```
Updated Score = Original Score + (Docking Weight × Normalized Docking Score)

Where:
- Docking Weight = 30%
- Normalized Docking Score = (Affinity - Min) / (Max - Min)
```

The platform integrates docking results into the overall candidate ranking, giving 30% weight to binding affinity.

---

### Statistical Summary Explained

| Metric | Value | Meaning |
|--------|-------|---------|
| **Mean Affinity** | 3.15 | Average across all 9 poses (skewed by bad poses) |
| **Std. Deviation** | ±9.45 | High variance = inconsistent poses |
| **Range** | 22.38 | Difference between best (-6.52) and worst (+15.86) |

**Interpretation**: The high standard deviation indicates some poses are artifacts. Focus on the best pose (-6.52 kcal/mol) for evaluation.

---

## Tools & Technologies

| Component | Tool | Version | License | Purpose |
|-----------|------|---------|---------|---------|
| **Docking Engine** | AutoDock Vina | 1.2.5 | Apache 2.0 | Core docking simulation |
| **Ligand Prep** | OpenBabel | 3.1.1 | GPL-2.0 | SMILES → 3D conversion |
| **Ligand Prep** | Meeko | 0.5.0 | Apache 2.0 | PDBQT preparation |
| **Protein Source** | AlphaFold DB | - | CC BY 4.0 | 3D protein structures |
| **Job Queue** | Celery | 5.3.6 | BSD | Background job processing |
| **Result Storage** | SQLite | - | Public Domain | Job and result persistence |

---

## File Formats

| Format | Extension | Used For |
|--------|-----------|----------|
| **SMILES** | (text) | Molecular structure as string |
| **PDB** | .pdb | Protein 3D coordinates |
| **PDBQT** | .pdbqt | Docking-ready format (with charges) |
| **SDF** | .sdf | 3D molecule with properties |

---

## Docking Job Lifecycle

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ PENDING │───▶│ QUEUED  │───▶│ RUNNING │───▶│ PARSING │───▶│COMPLETED│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼
  Job created   In Celery     Vina running   Extracting    Results
               queue          (5-30 min)     poses         available
```

**Failure states**: FAILED (error during execution), CANCELLED (user cancelled)

---

## Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Rigid protein** | Doesn't account for protein flexibility | Use ensemble docking (future) |
| **Scoring function** | Approximates real binding energy | Compare with experimental data |
| **Binding site unknown** | May dock to wrong location | Use known binding sites when available |
| **Solvent not modeled** | Ignores water-mediated interactions | Consider with caution |

---

## When to Trust Docking Results

✅ **Trust more when**:
- Multiple poses cluster together (low RMSD)
- Binding affinity < -7 kcal/mol
- Known binding site was used
- Results align with experimental data

⚠️ **Be cautious when**:
- High variance between poses
- Weak binding affinity (> -5 kcal/mol)
- RMSD values are very high
- Positive binding energies appear

---

## Quick Reference

**Good docking result**:
- Affinity: ≤ -7 kcal/mol
- Top poses cluster (RMSD < 2 Å)
- Consistent binding mode

**Your result (ORE-1001 for COVID-19)**:
- Affinity: -6.52 kcal/mol (Moderate)
- Top 4 poses cluster well
- Worth further investigation, but not a strong hit

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/docking/submit` | Submit docking job |
| GET | `/api/docking/status/{job_id}` | Check job status |
| GET | `/api/docking/results/{job_id}` | Get docking results |
| DELETE | `/api/docking/cancel/{job_id}` | Cancel running job |
| GET | `/api/docking/jobs` | List all user jobs |
