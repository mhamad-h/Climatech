import React from 'react';

const Loader = () => {
  return (
    <div className="flex items-center space-x-2 text-indigo-400 text-sm">
      {/* TODO: Replace with animated spinner component */}
      <span className="w-3 h-3 inline-block rounded-full bg-indigo-500 animate-pulse" />
      <span>Loading...</span>
    </div>
  );
};

export default Loader;
