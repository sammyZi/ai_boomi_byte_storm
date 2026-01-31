'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingIndicatorProps {
  message?: string;
  estimatedTime?: number;
}

export default function LoadingIndicator({
  message = 'Discovering drug candidates...',
  estimatedTime = 10,
}: LoadingIndicatorProps) {
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState(0);

  const stages = [
    'Identifying disease targets...',
    'Retrieving protein structures...',
    'Searching bioactive molecules...',
    'Analyzing molecular properties...',
    'Calculating scores...',
    'Ranking candidates...',
  ];

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return prev;
        return prev + (100 - prev) * 0.1;
      });
    }, 500);

    const stageInterval = setInterval(() => {
      setCurrentStage((prev) => (prev < stages.length - 1 ? prev + 1 : prev));
    }, (estimatedTime * 1000) / stages.length);

    return () => {
      clearInterval(progressInterval);
      clearInterval(stageInterval);
    };
  }, [estimatedTime, stages.length]);

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        {/* Spinner */}
        <div className="flex justify-center mb-6">
          <Loader2 className="w-16 h-16 text-blue-600 animate-spin" />
        </div>

        {/* Message */}
        <h3 className="text-xl font-semibold text-gray-900 text-center mb-2">{message}</h3>

        {/* Current Stage */}
        <p className="text-sm text-gray-600 text-center mb-6">{stages[currentStage]}</p>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Estimated Time */}
        <p className="text-xs text-gray-500 text-center">
          Estimated time: {estimatedTime} seconds
        </p>
      </div>
    </div>
  );
}
