# 🧬 AI-Powered Drug Discovery Platform

---

## 1. Problem Statement

Researchers exploring drug candidates for a disease must manually query multiple databases (Open Targets, ChEMBL, AlphaFold), cross-reference results, analyze molecular properties, and run docking simulations one by one. This repetitive process takes hours to days for each disease query.

**This tool automates the lookup, analysis, and molecular docking—returning ranked candidates in seconds and docking results in minutes instead of hours.**

---

## 2. Users & Context

### Target Users

| User | Need | How We Help |
|------|------|-------------|
| **Pharma R&D Teams** | Accelerate target identification | Automated pipeline, batch processing |
| **Biotech Startups** | Limited screening resources | Free tier, API access |
| **Academic Researchers** | Reduce repetitive manual work | One-click disease-to-drug search |
| **Biochemistry Students** | Learning tool for drug discovery | Visual results, AI explanations |

### Use Cases

- **Early-stage screening**: Quickly identify promising drug candidates for a disease
- **Target validation**: Verify protein targets with AlphaFold structures
- **Molecular docking**: Simulate drug-protein binding and predict binding affinity
- **Literature review acceleration**: AI-generated summaries of candidate potential
- **Educational demonstrations**: Teach drug discovery pipeline concepts

---

## 3. Solution Overview

**Input**: Disease name (e.g., "Alzheimer's disease")  
**Output**: Ranked list of drug candidates with scores, properties, AI analysis, and optional molecular docking results

### Pipeline Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Search  │───▶│ Targets  │───▶│ Molecules│───▶│ Analysis │───▶│  Score   │───▶│ Results  │
│ Disease  │    │ Proteins │    │ from DB  │    │ RDKit    │    │  Rank    │    │ Top 20   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                    │                │                │
                    ▼                ▼                ▼
              Open Targets       ChEMBL          BioMistral
              + AlphaFold                        AI Analysis
```

### Molecular Docking

After discovering candidates, users can submit them for molecular docking simulation.

**What it does**: Simulates how a drug molecule fits into a protein's binding site.

**How it works**:
1. Protein structure fetched from AlphaFold (PDB format)
2. Molecule converted to 3D structure (PDBQT format via OpenBabel)
3. AutoDock Vina calculates optimal binding poses
4. Results returned with binding affinity scores

**Docking Results Include**:

| Output | Description |
|--------|-------------|
| **Binding Affinity** | Energy score in kcal/mol (more negative = stronger binding, typically -6 to -12) |
| **Best Pose** | 3D coordinates of the drug molecule docked into the protein |
| **RMSD** | Root-mean-square deviation between poses (indicates pose consistency) |
| **Pose Count** | Multiple binding poses ranked by affinity |

**Timeline**: 5-30 minutes per job (runs in background via Celery queue)

### Architecture

```
Frontend (Next.js 14 + TypeScript + Tailwind)
                    │
                    ▼ REST API
Backend (FastAPI + Python 3.11)
    ├── Discovery Pipeline
    │   ├── Open Targets Client (disease → proteins)
    │   ├── AlphaFold Client (protein → 3D structure)
    │   ├── ChEMBL Client (protein → molecules)
    │   ├── RDKit Analyzer (molecule → properties)
    │   ├── Scoring Engine (properties → rank)
    │   └── BioMistral Engine (candidate → AI analysis)
    ├── Docking Service (AutoDock Vina + Celery)
    └── Cache Layer (Redis, 24-hour TTL)
```

---

## 4. Setup & Run

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (or Docker)
- Ollama (optional, for AI analysis)

### Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1    # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
docker-compose up -d           # Start Redis
python run.py                  # Start backend at localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev                    # Start frontend at localhost:3000
```

### Optional: AI Analysis

```bash
# Install Ollama from https://ollama.ai
ollama pull biomistral
```

### Verify Installation

1. Open `http://localhost:3000`
2. Search for "diabetes"
3. Results should appear in 8-10 seconds

---

## 5. Models & Data

### Data Sources

| Source | Data | License | URL |
|--------|------|---------|-----|
| **Open Targets** | Disease-protein associations | Apache 2.0 | https://platform.opentargets.org |
| **ChEMBL** | Bioactive molecules (2.4M compounds) | CC BY-SA 3.0 | https://www.ebi.ac.uk/chembl |
| **AlphaFold DB** | Protein 3D structures (200M proteins) | CC BY 4.0 | https://alphafold.ebi.ac.uk |

### AI Model

| Model | Purpose | License | Notes |
|-------|---------|---------|-------|
| **BioMistral-7B** | Drug candidate analysis | Apache 2.0 | Run locally via Ollama, no data sent externally |

### Cheminformatics

| Library | Purpose | License |
|---------|---------|---------|
| **RDKit** | Molecular property calculation | BSD-3-Clause |
| **OpenBabel** | Molecular format conversion | GPL-2.0 |
| **AutoDock Vina** | Molecular docking | Apache 2.0 |

### Scoring Algorithm

```
Composite Score = (0.40 × Binding) + (0.30 × Drug-likeness) + (0.20 × Safety) + (0.10 × Novelty)

Where:
- Binding: Normalized pChEMBL value (4-10 → 0-1)
- Drug-likeness: Lipinski's Rule of Five compliance
- Safety: Absence of toxicophores (10 patterns checked)
- Novelty: Structural uniqueness score
```

---

## 6. Evaluation & Guardrails

### AI Hallucination Mitigation

| Risk | Mitigation |
|------|------------|
| **Fabricated data** | AI only analyzes data from validated sources (ChEMBL, Open Targets) |
| **Incorrect analysis** | Validation layer checks AI output mentions correct molecule name and disease |
| **Generic responses** | Filter rejects responses that don't contain specific scientific content |
| **Timeout handling** | 30-second timeout with graceful fallback (results returned without AI analysis) |

### Bias Mitigation

| Risk | Mitigation |
|------|------------|
| **Database bias** | ChEMBL/Open Targets have established curation processes |
| **Scoring bias** | Transparent formula with published weights |
| **AI bias** | BioMistral trained on biomedical literature, not user data |

### Input Validation

- Disease names: 2-200 characters, sanitized
- Rate limiting: 100 requests/minute per IP
- SMILES validation: RDKit parser rejects malformed molecules

### Output Safeguards

- Medical disclaimer displayed prominently
- Results labeled as "computational predictions, not clinical recommendations"
- Export includes data provenance (source database, retrieval date)

---

## 7. Known Limitations & Risks

### Technical Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **External API dependency** | Service unavailable if Open Targets/ChEMBL down | 24-hour cache reduces impact |
| **AI analysis optional** | Requires Ollama + GPU for best performance | Works without AI (scoring still functions) |
| **Docking is slow** | 5-30 minutes per job | Background queue with status tracking |
| **Limited to known molecules** | Cannot predict novel compounds | Future: generative models |

### Scientific Limitations

| Limitation | Impact |
|------------|--------|
| **Computational predictions only** | Not validated in wet lab or clinical trials |
| **Binding affinity estimates** | pChEMBL values are experimental, but context-dependent |
| **No ADMET predictions** | Absorption, distribution, metabolism, excretion not modeled |
| **No off-target analysis** | Potential side effects not predicted |

### Risk Disclosure

⚠️ **This platform is for research and educational purposes only.**

- Drug candidates are computational predictions
- Results have NOT been validated through clinical trials
- Do NOT use for clinical decision-making
- Consult qualified professionals before any drug development

---

## 8. Team

| Name | Role | Contact |
|------|------|---------|
| **[Samarth Bhinge]** | Project Lead / Full-Stack Developer | bhingesamarth@gmail.com |
| **[Vedant Hande]** | Backend Developer | vedanthande2244@gmail.com |


### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open a Pull Request

### Support

- 📚 [Backend Documentation](backend/README.md)
- 📚 [Frontend Documentation](frontend/README.md)
- 📚 [API Documentation](backend/API_DOCUMENTATION.md)
- 🐛 [Report Issues](../../issues)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>Built for accelerating drug discovery research</strong>
</div>
