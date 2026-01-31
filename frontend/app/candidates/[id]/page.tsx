'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams, useParams } from 'next/navigation';
import useDiscovery from '@/hooks/useDiscovery';
import { DrugCandidate } from '@/types';
import LoadingIndicator from '@/components/LoadingIndicator';
import ErrorMessage from '@/components/ErrorMessage';
import ProteinViewer3D from '@/components/ProteinViewer3D';
import MoleculeViewer3D from '@/components/MoleculeViewer3D';
import {
    ArrowLeft,
    Share2,
    Download,
    Dna,
    Activity,
    FlaskConical,
    AlertTriangle,
    ShieldCheck,
    Brain,
    CheckCircle
} from 'lucide-react';

function CandidateDetailsContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const params = useParams();
    const id = params.id as string;
    const disease = searchParams.get('disease');

    const { data, isLoading, isError, error } = useDiscovery(disease || '');
    const [candidate, setCandidate] = useState<DrugCandidate | null>(null);

    useEffect(() => {
        if (data?.candidates) {
            const found = data.candidates.find(
                (c) => c.molecule.chembl_id === id
            );
            if (found) {
                setCandidate(found);
            }
        }
    }, [data, id]);

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
        <div className="min-h-screen bg-slate-50 pb-20">
            {/* Header Section */}
            <div className="bg-white border-b border-gray-200 shadow-sm sticky top-[64px] z-10 transition-all">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
                        <button
                            onClick={handleBack}
                            className="group flex items-center gap-2 text-gray-600 hover:text-primary-600 transition-colors"
                        >
                            <div className="p-2 rounded-full group-hover:bg-primary-50 transition-colors">
                                <ArrowLeft className="w-5 h-5" />
                            </div>
                            <span className="font-medium">Back to Results</span>
                        </button>

                        <div className="flex items-center gap-3">
                            <button className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all">
                                <Share2 className="w-5 h-5" />
                            </button>
                            <button className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all">
                                <Download className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

                {/* Title Area */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
                    <div className="lg:col-span-2 space-y-4">
                        <div className="flex items-start gap-4">
                            <div className="flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-2xl font-bold text-2xl shadow-lg">
                                #{candidate.rank}
                            </div>
                            <div>
                                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 leading-tight">
                                    {candidate.molecule.name}
                                </h1>
                                <div className="flex items-center gap-3 mt-2 text-gray-500 font-mono text-sm">
                                    <span className="bg-gray-100 px-2 py-1 rounded-md border border-gray-200">
                                        {candidate.molecule.chembl_id}
                                    </span>
                                    <span>•</span>
                                    <span>Top Candidate for {disease}</span>
                                </div>
                            </div>
                        </div>

                        <p className="text-lg text-gray-600 leading-relaxed max-w-2xl">
                            identified as a potent inhibitor with high binding affinity and favorable safety profile.
                        </p>

                        <div className="flex flex-wrap gap-3 mt-4">
                            <div className="px-4 py-2 bg-blue-50 text-blue-700 rounded-xl text-sm font-semibold border border-blue-200 flex items-center gap-2">
                                <Activity className="w-4 h-4" />
                                Binding Affinity: {candidate.binding_affinity_score}
                            </div>
                            <div className={`px-4 py-2 rounded-xl text-sm font-semibold border border-opacity-50 flex items-center gap-2 ${candidate.toxicity.risk_level === 'low' ? 'bg-green-50 text-green-700 border-green-200' :
                                candidate.toxicity.risk_level === 'medium' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                                    'bg-red-50 text-red-700 border-red-200'
                                }`}>
                                <ShieldCheck className="w-4 h-4" />
                                Risk Level: {candidate.toxicity.risk_level.toUpperCase()}
                            </div>
                        </div>
                    </div>

                    {/* Score Card */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 flex flex-col justify-center">
                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Composite Score</h3>
                        <div className="flex items-end gap-3 mb-2">
                            <span className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                                {candidate.composite_score.toFixed(1)}
                            </span>
                            <span className="text-gray-400 text-xl font-medium mb-2">/ 10</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2 mb-6 overflow-hidden">
                            <div
                                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2 rounded-full transition-all duration-1000 ease-out"
                                style={{ width: `${Math.min(candidate.composite_score * 10, 100)}%` }}
                            ></div>
                        </div>

                        <div className="space-y-3 pt-4 border-t border-gray-100">
                            <div>
                                <div className="flex justify-between items-center mb-1">
                                    <span className="text-xs font-semibold text-gray-600 uppercase">Binding Affinity</span>
                                    <span className="text-xs font-bold text-gray-900">{candidate.binding_affinity_score}</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                    <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: `${Math.min(parseFloat(candidate.binding_affinity_score + "") * 10, 100)}%` }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between items-center mb-1">
                                    <span className="text-xs font-semibold text-gray-600 uppercase">Drug Likeness</span>
                                    <span className="text-xs font-bold text-gray-900">{candidate.properties.drug_likeness_score.toFixed(2)}</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${candidate.properties.drug_likeness_score * 100}%` }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between items-center mb-1">
                                    <span className="text-xs font-semibold text-gray-600 uppercase">Safety Score</span>
                                    <span className="text-xs font-bold text-gray-900">{(1 - candidate.toxicity.toxicity_score).toFixed(2)}</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                    <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${(1 - candidate.toxicity.toxicity_score) * 100}%` }}></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Grid */}
                <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">

                    {/* Left Column - Details */}
                    <div className="xl:col-span-7 space-y-8">

                        {/* 3D Protein Structure - Primary View */}
                        {candidate.target.uniprot_id && (
                            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                                <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gradient-to-r from-white to-gray-50">
                                    <div>
                                        <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                            <div className="w-2 h-2 bg-indigo-600 rounded-full animate-pulse"></div>
                                            Target Protein Structure
                                        </h2>
                                        <p className="text-sm text-gray-500 mt-1">{candidate.target.protein_name} ({candidate.target.uniprot_id})</p>
                                    </div>
                                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full">
                                        Interactive 3D
                                    </span>
                                </div>
                                <div className="p-1 bg-gray-50">
                                    <ProteinViewer3D
                                        uniprotId={candidate.target.uniprot_id}
                                        proteinName={candidate.target.protein_name}
                                    />
                                </div>
                            </div>
                        )}

                        {/* AI Analysis */}
                        <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-sm relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-8 opacity-5">
                                <Brain className="w-32 h-32" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                                <div className="p-2 bg-purple-100 rounded-lg text-purple-600">
                                    <Brain className="w-6 h-6" />
                                </div>
                                AI Analysis
                            </h3>
                            <div className="prose prose-blue max-w-none text-gray-600 bg-purple-50 p-6 rounded-xl border border-purple-100">
                                <p className="leading-relaxed whitespace-pre-line">
                                    {candidate.ai_analysis || "No AI analysis available for this candidate."}
                                </p>
                            </div>
                        </div>

                        {/* Target Information Detail */}
                        <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-sm">
                            <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                                <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
                                    <Dna className="w-6 h-6" />
                                </div>
                                Detailed Target Information
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                                    <span className="text-sm font-medium text-gray-500 block mb-1">Gene Symbol</span>
                                    <span className="text-lg font-bold text-gray-900">{candidate.target.gene_symbol}</span>
                                </div>
                                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                                    <span className="text-sm font-medium text-gray-500 block mb-1">Confidence Score</span>
                                    <span className="text-lg font-bold text-gray-900">{(candidate.target.confidence_score * 100).toFixed(0)}%</span>
                                </div>
                                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 md:col-span-2">
                                    <span className="text-sm font-medium text-gray-500 block mb-1">Target Name</span>
                                    <span className="text-lg font-bold text-gray-900 break-words">{candidate.target.protein_name}</span>
                                </div>
                            </div>
                        </div>

                    </div>

                    {/* Right Column - Side Details */}
                    <div className="xl:col-span-5 space-y-8">

                        {/* Molecule Structure */}
                        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                            <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-white to-gray-50">
                                <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                    <FlaskConical className="w-5 h-5 text-teal-600" />
                                    Molecule Structure
                                </h2>
                            </div>
                            <div className="p-1 bg-gray-50">
                                <MoleculeViewer3D
                                    smiles={candidate.molecule.smiles}
                                    moleculeName={candidate.molecule.name}
                                />
                            </div>
                            <div className="p-4 bg-white border-t border-gray-200">
                                <div className="text-xs text-gray-500 font-mono break-all bg-gray-50 p-3 rounded-lg border border-gray-200">
                                    SMILES: {candidate.molecule.smiles}
                                </div>
                            </div>
                        </div>

                        {/* Molecular Properties */}
                        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                            <h3 className="text-lg font-bold text-gray-900 mb-5">Molecular Properties</h3>
                            <dl className="space-y-4">
                                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                                    <dt className="text-gray-600 font-medium">Molecular Weight</dt>
                                    <dd className="font-mono font-semibold text-gray-900">{candidate.properties.molecular_weight.toFixed(2)} Da</dd>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                                    <dt className="text-gray-600 font-medium">LogP (Lipophilicity)</dt>
                                    <dd className="font-mono font-semibold text-gray-900">{candidate.properties.logp.toFixed(2)}</dd>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                                    <dt className="text-gray-600 font-medium">TPSA</dt>
                                    <dd className="font-mono font-semibold text-gray-900">{candidate.properties.tpsa.toFixed(2)}</dd>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                                    <dt className="text-gray-600 font-medium">Lipinski Violations</dt>
                                    <dd className="font-bold text-gray-900">{candidate.properties.lipinski_violations}</dd>
                                </div>
                                <div className="flex justify-between items-center py-2">
                                    <dt className="text-gray-600 font-medium">QED (Drug-likeness)</dt>
                                    <dd className="font-mono font-semibold text-blue-600">{candidate.properties.drug_likeness_score.toFixed(2)}</dd>
                                </div>
                            </dl>
                        </div>

                        {/* Toxicity Warning */}
                        <div className={`rounded-2xl p-6 border-2 ${candidate.toxicity.risk_level === 'low' ? 'bg-green-50 border-green-200' :
                            candidate.toxicity.risk_level === 'medium' ? 'bg-yellow-50 border-yellow-200' :
                                'bg-red-50 border-red-200'
                            }`}>
                            <h3 className={`text-lg font-bold mb-4 flex items-center gap-2 ${candidate.toxicity.risk_level === 'low' ? 'text-green-900' :
                                candidate.toxicity.risk_level === 'medium' ? 'text-yellow-900' :
                                    'text-red-900'
                                }`}>
                                <AlertTriangle className="w-5 h-5" />
                                Safety Assessment
                            </h3>

                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-sm font-medium opacity-80">Toxicity Score</span>
                                    <span className="font-bold">{candidate.toxicity.toxicity_score}</span>
                                </div>

                                {candidate.toxicity.detected_toxicophores.length > 0 ? (
                                    <div>
                                        <span className="text-sm font-medium opacity-80 block mb-2">Detected Toxicophores:</span>
                                        <div className="flex flex-wrap gap-2">
                                            {candidate.toxicity.detected_toxicophores.map((t, i) => (
                                                <span key={i} className="px-2 py-1 bg-white bg-opacity-60 rounded text-xs font-semibold border border-black border-opacity-10">
                                                    {t}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-sm font-medium flex items-center gap-2">
                                        <CheckCircle className="w-4 h-4" />
                                        No toxicophores detected
                                    </p>
                                )}
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
