import React from 'react';

const ResultsDisplay = ({ data }) => {
  return (
    <div className="text-gray-200 text-sm">
      ResultsDisplay Component
      {/* TODO: Render probability, confidence, and summary in a styled card layout. */}
      {/* Potential additions: visual gauge, precipitation timeline, confidence badge. */}
      {/* Data prop example shape: { rainProbability: number, confidence: string, summary: string } */}
      {data && (
        <pre className="mt-2 text-xs bg-slate-800 p-3 rounded overflow-auto max-h-64">{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
};

export default ResultsDisplay;
