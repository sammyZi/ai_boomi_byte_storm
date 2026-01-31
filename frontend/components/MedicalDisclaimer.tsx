'use client';

import { useState, useEffect } from 'react';
import { X, AlertTriangle } from 'lucide-react';

export default function MedicalDisclaimer() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if disclaimer has been dismissed
    const dismissed = localStorage.getItem('disclaimer-dismissed');
    if (!dismissed) {
      setIsVisible(true);
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem('disclaimer-dismissed', 'true');
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-yellow-50 border-t-4 border-yellow-400 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-yellow-900 mb-2">
                Medical Disclaimer - Research Purposes Only
              </h3>
              <div className="text-sm text-yellow-800 space-y-2">
                <p>
                  <strong>This platform is for research and educational purposes only.</strong>{' '}
                  The information provided should not be used for medical diagnosis or treatment.
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Results are computational predictions and require experimental validation</li>
                  <li>Not a substitute for professional medical advice or clinical trials</li>
                  <li>Drug candidates require extensive testing before clinical use</li>
                  <li>Consult qualified healthcare professionals for medical decisions</li>
                </ul>
              </div>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="ml-4 flex-shrink-0 text-yellow-600 hover:text-yellow-800 transition-colors"
            aria-label="Dismiss disclaimer"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>
    </div>
  );
}
