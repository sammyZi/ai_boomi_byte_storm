import { Database, Cpu, Microscope, Shield } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-4xl font-bold text-gray-900 mb-6">
        About the AI-Powered Drug Discovery Platform
      </h1>

      <div className="prose prose-lg max-w-none">
        <p className="text-xl text-gray-600 mb-8">
          This platform implements a complete proteome-to-cure pipeline, transforming disease
          queries into ranked drug candidates in 8-10 seconds through the integration of multiple
          biomedical databases and AI-powered analysis.
        </p>

        <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How It Works</h2>

        <div className="space-y-6 mb-12">
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Database className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                1. Target Identification
              </h3>
              <p className="text-gray-600">
                We query the Open Targets Platform to identify protein targets associated with
                your disease query. Targets are filtered by confidence score and ranked to focus
                on the most promising therapeutic intervention points.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Microscope className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                2. Structure Retrieval
              </h3>
              <p className="text-gray-600">
                For each target, we retrieve 3D protein structures from the AlphaFold Database.
                These structures help understand binding sites and structural features relevant to
                drug design.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Cpu className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                3. Molecule Discovery
              </h3>
              <p className="text-gray-600">
                We search the ChEMBL Database for bioactive molecules that have been tested
                against the identified targets. Molecules are filtered by activity level and
                validated for chemical structure integrity.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                4. Analysis & Ranking
              </h3>
              <p className="text-gray-600">
                Using RDKit, we calculate molecular properties and assess drug-likeness using
                Lipinski's Rule of Five. We screen for toxic substructures and generate composite
                scores combining binding affinity, drug-likeness, and safety. Finally, BioMistral-7B
                provides AI-powered analysis of the top candidates.
              </p>
            </div>
          </div>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Data Sources</h2>

        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <ul className="space-y-3">
            <li>
              <strong className="text-gray-900">Open Targets Platform:</strong>{' '}
              <span className="text-gray-600">
                Disease-target associations with evidence from genetics, literature, and pathways
              </span>
            </li>
            <li>
              <strong className="text-gray-900">ChEMBL Database:</strong>{' '}
              <span className="text-gray-600">
                Bioactive molecules with activity data from medicinal chemistry literature
              </span>
            </li>
            <li>
              <strong className="text-gray-900">AlphaFold Database:</strong>{' '}
              <span className="text-gray-600">
                Predicted 3D protein structures with confidence scores
              </span>
            </li>
            <li>
              <strong className="text-gray-900">BioMistral-7B:</strong>{' '}
              <span className="text-gray-600">
                Biomedical language model for generating detailed candidate analysis
              </span>
            </li>
          </ul>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Methodology</h2>

        <p className="text-gray-600 mb-4">
          Our platform uses a composite scoring system to rank drug candidates:
        </p>

        <ul className="list-disc list-inside space-y-2 text-gray-600 mb-8">
          <li>
            <strong>40% Binding Affinity:</strong> Normalized from pChEMBL values (IC50, Ki, Kd)
          </li>
          <li>
            <strong>30% Drug-Likeness:</strong> Based on Lipinski's Rule of Five compliance
          </li>
          <li>
            <strong>20% Safety:</strong> Inverse of toxicity score from SMARTS pattern matching
          </li>
          <li>
            <strong>10% Novelty:</strong> Encourages exploration of new chemical space
          </li>
        </ul>

        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6 mb-8">
          <h3 className="text-lg font-semibold text-yellow-900 mb-2">Important Disclaimer</h3>
          <p className="text-yellow-800">
            This platform is for research and educational purposes only. Results are computational
            predictions that require extensive experimental validation before any clinical
            application. Always consult qualified healthcare professionals for medical decisions.
          </p>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Contact</h2>

        <p className="text-gray-600">
          For questions, feedback, or collaboration opportunities, please contact us at{' '}
          <a
            href="mailto:support@drugdiscovery.example.com"
            className="text-blue-600 hover:underline"
          >
            support@drugdiscovery.example.com
          </a>
        </p>
      </div>
    </div>
  );
}
