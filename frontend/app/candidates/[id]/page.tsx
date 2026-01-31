'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams, useParams } from 'next/navigation';
import useDiscovery from '@/hooks/useDiscovery';
import { DrugCandidate } from '@/types';
import LoadingIndicator from '@/components/LoadingIndicator';
import ErrorMessage from '@/components/ErrorMessage';
import ProteinViewer3D from '@/components/ProteinViewer3D';
import MoleculeViewer3D from '@/components/MoleculeViewer3D';
import DiscoveryAPI from '@/lib/discovery-api';
import {
    ArrowLeft,
    Dna,
    FlaskConical,
    AlertTriangle,
    Brain,
    CheckCircle,
    Loader2
} from 'lucide-react';

function CandidateDetailsContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const params = useParams();
    const id = params.id as string;
    const disease = searchParams.get('disease');

    const { data, isLoading, isError, error } = useDiscovery(disease || '');
    const [candidate, setCandidate] = useState<DrugCandidate | null>(null);
    
    // AI Analysis state
    const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
    const [isLoadingAiAnalysis, setIsLoadingAiAnalysis] = useState(false);
    const [aiAnalysisError, setAiAnalysisError] = useState<string | null>(null);

    useEffect(() => {
        if (data?.candidates) {
            const found = data.candidates.find(
                (c) => c.molecule.chembl_id === id
            );
            if (found) {
                setCandidate(found);
                // If candidate already has AI analysis from backend, use it
                if (found.ai_analysis) {
                    setAiAnalysis(found.ai_analysis);
                }
            }
        }
    }, [data, id]);

    // Fetch AI analysis on-demand when candidate is loaded
    useEffect(() => {
        const fetchAiAnalysis = async () => {
            if (candidate && !aiAnalysis && !isLoadingAiAnalysis) {
                setIsLoadingAiAnalysis(true);
                setAiAnalysisError(null);
                
                try {
                    const response = await DiscoveryAPI.analyzeCandidate(candidate);
                    if (response.success && response.ai_analysis) {
                        setAiAnalysis(response.ai_analysis);
                    } else {
                        setAiAnalysisError(response.message || 'AI analysis unavailable');
                    }
                } catch (err) {
                    setAiAnalysisError('Failed to generate AI analysis');
                } finally {
                    setIsLoadingAiAnalysis(false);
                }
            }
        };

        fetchAiAnalysis();
    }, [candidate, aiAnalysis, isLoadingAiAnalysis]);

    const handleBack = () => {
        if (disease) {
            router.push(`/results?q=${encodeURIComponent(disease)}`);
        } else {
            router.push('/');
        }
    };

    if (!disease) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <ErrorMessage
                    error={{
                        error_code: 'MISSING_PARAMS',
                        message: 'No disease context found. Redirecting to home...',
                        timestamp: new Date().toISOString()
                    }}
                />
                <button onClick={() => router.push('/')} className="mt-4 text-primary-600 hover:underline">
                    Go Home
                </button>
            </div>
        )
    }

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <LoadingIndicator message="Loading candidate details..." />
            </div>
        );
    }

    if (isError || !candidate) {
        if (!isLoading && !candidate && data) {
            return (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="text-center">
                        <h2 className="text-2xl font-bold text-gray-900">Candidate Not Found</h2>
                        <p className="mt-2 text-gray-600">Could not find candidate with ID {id} for disease {disease}.</p>
                        <button
                            onClick={handleBack}
                            className="mt-6 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                        >
                            Back to Results
                        </button>
                    </div>
                </div>
            )
        }
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <ErrorMessage
                    error={error || {
                        error_code: 'DATA_UNAVAILABLE',
                        message: 'The candidate data is currently unavailable.',
                        timestamp: new Date().toISOString()
                    }}
                />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-blue-50 via-white to-gray-50 pb-20 pt-24">
            {/* Header Section */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-8">
                <button
                    onClick={handleBack}
                    className="group flex items-center gap-2 text-gray-600 hover:text-blue-600 transition-colors mb-6"
                >
                    <div className="p-2 rounded-xl group-hover:bg-blue-50 transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                    <span className="font-semibold">Back to Results</span>
                </button>

                {/* Title Card */}
                <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-blue-100 shadow-lg">
                    <div className="flex items-start gap-4">
                        <div className="flex items-center justify-center w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-xl font-bold text-xl shadow-md shadow-blue-500/30">
                            #{candidate.rank}
                        </div>
                        <div className="flex-1">
                            <h1 className="text-2xl font-bold text-gray-900 mb-2">
                                {candidate.molecule.name}
                            </h1>
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                                <span className="bg-gray-100 px-2.5 py-1 rounded-lg border border-gray-200 font-mono font-semibold text-gray-700">
                                    {candidate.molecule.chembl_id}
                                </span>
                                <span className="text-gray-400">•</span>
                                <span className="text-gray-600">Top candidate for <span className="font-semibold text-blue-600">{disease}</span></span>
                            </div>
                            
                            {/* Score Badges */}
                            <div className="flex flex-wrap gap-2 mt-4">
                                <div className="px-3 py-1.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg text-xs font-bold shadow-sm">
                                    Score: {candidate.composite_score.toFixed(1)}/10
                                </div>
                                <div className="px-3 py-1.5 bg-purple-50 text-purple-700 rounded-lg text-xs font-semibold border border-purple-200">
                                    Binding: {candidate.binding_affinity_score}
                                </div>
                                <div className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${
                                    candidate.toxicity.risk_level === 'low' ? 'bg-green-50 text-green-700 border-green-200' :
                                    candidate.toxicity.risk_level === 'medium' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                                    'bg-red-50 text-red-700 border-red-200'
                                }`}>
                                    Risk: {candidate.toxicity.risk_level.toUpperCase()}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Properties Grid - Top Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    
                    {/* Molecular Properties */}
                    <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-5 border border-blue-100 shadow-lg">
                        <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <FlaskConical className="w-5 h-5 text-blue-600" />
                            Molecular Properties
                        </h3>
                        <dl className="space-y-3">
                            <div className="flex justify-between items-center p-2.5 bg-blue-50 rounded-lg border border-blue-200">
                                <dt className="text-xs font-semibold text-gray-700">Molecular Weight</dt>
                                <dd className="font-mono font-bold text-gray-900 text-sm">{candidate.properties.molecular_weight.toFixed(2)} <span className="text-xs text-gray-500">Da</span></dd>
                            </div>
                            <div className="flex justify-between items-center p-2.5 bg-indigo-50 rounded-lg border border-indigo-200">
                                <dt className="text-xs font-semibold text-gray-700">LogP (Lipophilicity)</dt>
                                <dd className="font-mono font-bold text-gray-900 text-sm">{candidate.properties.logp.toFixed(2)}</dd>
                            </div>
                            <div className="flex justify-between items-center p-2.5 bg-purple-50 rounded-lg border border-purple-200">
                                <dt className="text-xs font-semibold text-gray-700">TPSA</dt>
                                <dd className="font-mono font-bold text-gray-900 text-sm">{candidate.properties.tpsa.toFixed(2)}</dd>
                            </div>
                            <div className="flex justify-between items-center p-2.5 bg-pink-50 rounded-lg border border-pink-200">
                                <dt className="text-xs font-semibold text-gray-700">Lipinski Violations</dt>
                                <dd className="font-bold text-gray-900 text-sm">{candidate.properties.lipinski_violations}</dd>
                            </div>
                            <div className="flex justify-between items-center p-2.5 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border-2 border-blue-300">
                                <dt className="text-xs font-semibold text-gray-700">QED (Drug-likeness)</dt>
                                <dd className="font-mono font-bold text-blue-600 text-base">{candidate.properties.drug_likeness_score.toFixed(2)}</dd>
                            </div>
                        </dl>
                    </div>

                    {/* Safety Assessment */}
                    <div className={`rounded-2xl p-5 border-2 shadow-lg ${
                        candidate.toxicity.risk_level === 'low' ? 'bg-green-50 border-green-300' :
                        candidate.toxicity.risk_level === 'medium' ? 'bg-yellow-50 border-yellow-300' :
                        'bg-red-50 border-red-300'
                    }`}>
                        <h3 className={`text-base font-bold mb-4 flex items-center gap-2 ${
                            candidate.toxicity.risk_level === 'low' ? 'text-green-900' :
                            candidate.toxicity.risk_level === 'medium' ? 'text-yellow-900' :
                            'text-red-900'
                        }`}>
                            <AlertTriangle className="w-5 h-5" />
                            Safety Assessment
                        </h3>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center p-2.5 bg-white/60 rounded-lg border border-white/40">
                                <span className="text-xs font-semibold">Toxicity Score</span>
                                <span className="font-bold text-base">{candidate.toxicity.toxicity_score.toFixed(2)}</span>
                            </div>

                            <div className="flex justify-between items-center p-2.5 bg-white/60 rounded-lg border border-white/40">
                                <span className="text-xs font-semibold">Risk Level</span>
                                <span className={`font-bold text-sm uppercase px-2.5 py-1 rounded-lg ${
                                    candidate.toxicity.risk_level === 'low' ? 'bg-green-200 text-green-900' :
                                    candidate.toxicity.risk_level === 'medium' ? 'bg-yellow-200 text-yellow-900' :
                                    'bg-red-200 text-red-900'
                                }`}>
                                    {candidate.toxicity.risk_level}
                                </span>
                            </div>

                            {candidate.toxicity.detected_toxicophores.length > 0 ? (
                                <div className="p-2.5 bg-white/60 rounded-lg border border-white/40">
                                    <span className="text-xs font-semibold block mb-2">Detected Toxicophores:</span>
                                    <div className="flex flex-wrap gap-1.5">
                                        {candidate.toxicity.detected_toxicophores.map((t, i) => (
                                            <span key={i} className="px-2.5 py-1 bg-white rounded-lg text-xs font-bold border border-gray-300 shadow-sm">
                                                {t}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="p-2.5 bg-white/60 rounded-lg border border-white/40">
                                    <p className="text-xs font-semibold flex items-center gap-2">
                                        <CheckCircle className="w-4 h-4" />
                                        No toxicophores detected
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Target Info & AI Analysis */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    {/* Target Information */}
                    <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-5 border border-blue-100 shadow-lg">
                        <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <Dna className="w-5 h-5 text-blue-600" />
                            Target Information
                        </h3>
                        <div className="space-y-2.5">
                            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                                <span className="text-xs font-semibold text-blue-600 block mb-1">Gene Symbol</span>
                                <span className="text-base font-bold text-gray-900">{candidate.target.gene_symbol}</span>
                            </div>
                            <div className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                                <span className="text-xs font-semibold text-indigo-600 block mb-1">Confidence Score</span>
                                <span className="text-base font-bold text-gray-900">{(candidate.target.confidence_score * 100).toFixed(0)}%</span>
                            </div>
                            <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                                <span className="text-xs font-semibold text-purple-600 block mb-1">Protein Name</span>
                                <span className="text-xs font-bold text-gray-900 break-words">{candidate.target.protein_name}</span>
                            </div>
                        </div>
                    </div>

                    {/* AI Analysis */}
                    <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-5 border border-blue-100 shadow-lg">
                        <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <Brain className="w-5 h-5 text-purple-600" />
                            AI Analysis
                        </h3>
                        <div className="bg-purple-50 p-4 rounded-lg border border-purple-200 max-h-64 overflow-y-auto">
                            {isLoadingAiAnalysis ? (
                                <div className="flex flex-col items-center justify-center py-8 space-y-3">
                                    <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
                                    <p className="text-sm text-purple-700 font-medium">Generating AI analysis...</p>
                                    <p className="text-xs text-gray-500">This may take a few moments</p>
                                </div>
                            ) : aiAnalysis ? (
                                <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-line">
                                    {aiAnalysis}
                                </p>
                            ) : aiAnalysisError ? (
                                <div className="text-xs text-gray-600 space-y-2">
                                    <p className="text-amber-600 font-semibold flex items-center gap-2">
                                        <AlertTriangle className="w-4 h-4" />
                                        {aiAnalysisError}
                                    </p>
                                    <p className="font-semibold">
                                        {candidate.molecule.name} shows {candidate.molecule.pchembl_value >= 7 ? 'strong' : candidate.molecule.pchembl_value >= 6 ? 'moderate' : 'weak'} binding affinity (pChEMBL: {candidate.molecule.pchembl_value.toFixed(1)}) to {candidate.target.gene_symbol}.
                                    </p>
                                    <p>
                                        Drug-likeness score of {candidate.properties.drug_likeness_score.toFixed(2)} with {candidate.properties.lipinski_violations} Lipinski violation{candidate.properties.lipinski_violations !== 1 ? 's' : ''}.
                                    </p>
                                    <p>
                                        Safety profile indicates <span className={`font-bold ${
                                            candidate.toxicity.risk_level === 'low' ? 'text-green-700' :
                                            candidate.toxicity.risk_level === 'medium' ? 'text-yellow-700' :
                                            'text-red-700'
                                        }`}>{candidate.toxicity.risk_level} risk</span> with toxicity score of {candidate.toxicity.toxicity_score.toFixed(2)}.
                                    </p>
                                </div>
                            ) : (
                                <div className="text-xs text-gray-600 space-y-2">
                                    <p className="font-semibold">
                                        {candidate.molecule.name} shows {candidate.molecule.pchembl_value >= 7 ? 'strong' : candidate.molecule.pchembl_value >= 6 ? 'moderate' : 'weak'} binding affinity (pChEMBL: {candidate.molecule.pchembl_value.toFixed(1)}) to {candidate.target.gene_symbol}.
                                    </p>
                                    <p>
                                        Drug-likeness score of {candidate.properties.drug_likeness_score.toFixed(2)} with {candidate.properties.lipinski_violations} Lipinski violation{candidate.properties.lipinski_violations !== 1 ? 's' : ''}.
                                    </p>
                                    <p>
                                        Safety profile indicates <span className={`font-bold ${
                                            candidate.toxicity.risk_level === 'low' ? 'text-green-700' :
                                            candidate.toxicity.risk_level === 'medium' ? 'text-yellow-700' :
                                            'text-red-700'
                                        }`}>{candidate.toxicity.risk_level} risk</span> with toxicity score of {candidate.toxicity.toxicity_score.toFixed(2)}.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* 3D Structures - Bottom Section */}
                <div className="mb-8">
                    <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <div className="w-1 h-6 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-full"></div>
                        3D Molecular Structures
                    </h2>
                    
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Protein Structure */}
                        {candidate.target.uniprot_id && (
                            <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-blue-200 shadow-lg overflow-hidden">
                                <div className="p-4 border-b border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                                        <Dna className="w-4 h-4 text-blue-600" />
                                        Target Protein Structure
                                    </h3>
                                    <p className="text-xs text-gray-600 mt-1 font-semibold">{candidate.target.protein_name}</p>
                                    <p className="text-xs text-gray-500 mt-0.5 font-mono">UniProt: {candidate.target.uniprot_id}</p>
                                </div>
                                <div className="p-2 bg-gray-50">
                                    <ProteinViewer3D
                                        uniprotId={candidate.target.uniprot_id}
                                        proteinName={candidate.target.protein_name}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Molecule Structure */}
                        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-teal-200 shadow-lg overflow-hidden">
                            <div className="p-4 border-b border-teal-200 bg-gradient-to-r from-teal-50 to-cyan-50">
                                <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                                    <FlaskConical className="w-4 h-4 text-teal-600" />
                                    Drug Molecule Structure
                                </h3>
                                <p className="text-xs text-gray-600 mt-1 font-semibold">{candidate.molecule.name}</p>
                                <p className="text-xs text-gray-500 mt-0.5 font-mono">ChEMBL: {candidate.molecule.chembl_id}</p>
                            </div>
                            <div className="p-2 bg-gray-50">
                                <MoleculeViewer3D
                                    smiles={candidate.molecule.smiles}
                                    moleculeName={candidate.molecule.name}
                                />
                            </div>
                            <div className="p-3 bg-white border-t border-teal-200">
                                <div className="text-xs text-gray-600 font-mono break-all bg-teal-50 p-2.5 rounded-lg border border-teal-200">
                                    <span className="text-teal-700 font-bold">SMILES:</span> {candidate.molecule.smiles}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function CandidateDetailsPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen bg-white flex items-center justify-center">
                    <LoadingIndicator message="Initializing..." />
                </div>
            }
        >
            <CandidateDetailsContent />
        </Suspense>
    );
}
