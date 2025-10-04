import React from 'react';

const Loader = ({ message = "Loading forecast...", size = "md" }) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12"
  };

  return (
    <div className="flex flex-col items-center justify-center py-12">
      {/* Animated spinner */}
      <div className={`${sizeClasses[size]} border-4 border-gray-600 border-t-blue-500 rounded-full animate-spin mb-4`}></div>
      
      {/* Loading message */}
      <p className="text-gray-300 text-center mb-2">{message}</p>
      
      {/* Animated dots */}
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-75"></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-150"></div>
      </div>
      
      {/* Progress steps (optional) */}
      <div className="mt-6 text-xs text-gray-500 text-center max-w-md">
        <div className="space-y-1">
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>Fetching location data</span>
          </div>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span>Processing weather patterns</span>
          </div>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            <span>Generating predictions</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Loader;
