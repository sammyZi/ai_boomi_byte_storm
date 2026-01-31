import { useState } from 'react';
import { DiscoveryResponse, DrugCandidate } from '@/types';

export function useExport() {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const exportToJSON = (data: DiscoveryResponse, filename?: string) => {
    try {
      setIsExporting(true);
      setError(null);

      const jsonString = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `drug-discovery-${data.query}-${Date.now()}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
      setIsExporting(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export JSON');
      setIsExporting(false);
    }
  };

  const exportToCSV = (data: DiscoveryResponse, filename?: string) => {
    try {
      setIsExporting(true);
      setError(null);

      // CSV headers
      const headers = [
        'Rank',
        'Molecule Name',
        'ChEMBL ID',
        'SMILES',
        'Composite Score',
        'Binding Affinity',
        'Drug Likeness',
        'Toxicity Score',
        'Risk Level',
        'Target Gene',
        'Target Protein',
        'Molecular Weight',
        'LogP',
        'HBD',
        'HBA',
        'TPSA',
        'Lipinski Violations',
      ];

      // Convert candidates to CSV rows
      const rows = data.candidates.map((candidate: DrugCandidate) => [
        candidate.rank,
        escapeCSV(candidate.molecule.name),
        candidate.molecule.chembl_id,
        escapeCSV(candidate.molecule.smiles),
        candidate.composite_score.toFixed(2),
        candidate.binding_affinity_score.toFixed(2),
        candidate.properties.drug_likeness_score.toFixed(2),
        candidate.toxicity.toxicity_score.toFixed(2),
        candidate.toxicity.risk_level,
        candidate.target.gene_symbol,
        escapeCSV(candidate.target.protein_name),
        candidate.properties.molecular_weight.toFixed(2),
        candidate.properties.logp.toFixed(2),
        candidate.properties.hbd,
        candidate.properties.hba,
        candidate.properties.tpsa.toFixed(2),
        candidate.properties.lipinski_violations,
      ]);

      // Combine headers and rows
      const csvContent = [headers, ...rows].map((row) => row.join(',')).join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `drug-discovery-${data.query}-${Date.now()}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
      setIsExporting(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export CSV');
      setIsExporting(false);
    }
  };

  return {
    exportToJSON,
    exportToCSV,
    isExporting,
    error,
  };
}

// Helper function to escape CSV values
function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export default useExport;
