import { useState } from 'react';
import { PipelineResponse } from '../types';

export const usePipelineResult = () => {
  const [data, setData] = useState<PipelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [step, setStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const runPipeline = async (file: File) => {
    setLoading(true);
    setError(null);
    setData(null);

    // Simulated real-time phase updates for the supervisor walkthrough
    const steps = [
      'Layer 1: Structural Extraction & Cleaning...',
      'Layer 1: Ingesting Hard Rules Vector Grid...',
      'Layer 2: Triggering Remote University Qwen-35B Engine...',
      'Layer 3: Computing Calibrated Rejection Matrices...'
    ];

    let currentStep = 0;
    setStep(steps[currentStep]);
    const stepInterval = setInterval(() => {
      if (currentStep < steps.length - 1) {
        currentStep++;
        setStep(steps[currentStep]);
      }
    }, 1500);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Backend Pipeline Server returned an error status.');
      const result: PipelineResponse = await response.json();
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Pipeline runtime dropped connection.');
    } finally {
      clearInterval(stepInterval);
      setLoading(false);
      setStep('');
    }
  };

  return { data, loading, step, error, runPipeline };
};
