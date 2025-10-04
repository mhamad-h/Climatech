import React, { useState } from 'react';
// import LocationInput from './components/LocationInput.jsx';
// import EventDatePicker from './components/EventDatePicker.jsx';
// import ResultsDisplay from './components/ResultsDisplay.jsx';
// import Loader from './components/Loader.jsx';
// import { getRainPrediction } from './services/api.js';

function App() {
  // Form state placeholders
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [eventDate, setEventDate] = useState('');

  // API interaction state placeholders
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    // TODO: Validate inputs (coordinate ranges, date format, etc.)
    // TODO: Call getRainPrediction({ latitude, longitude, eventDate })
    // setLoading(true);
    // try {
    //   const data = await getRainPrediction({ latitude, longitude, eventDate });
    //   setResult(data);
    // } catch (err) {
    //   setError(err.message || 'Request failed');
    // } finally {
    //   setLoading(false);
    // }
  };

  return (
    <div className="min-h-screen px-4 py-10 md:px-8 bg-space-bg">
      <header className="max-w-3xl mx-auto mb-10 text-center">
        <h1 className="text-3xl md:text-5xl font-bold text-white tracking-tight">Will it Rain on My Parade?</h1>
        <p className="mt-4 text-gray-400">NASA Space Apps Challenge Skeleton – React + FastAPI</p>
      </header>

      <main className="max-w-3xl mx-auto space-y-8">
        <section className="p-6 rounded-lg bg-space-panel shadow-lg border border-slate-700">
          <h2 className="text-xl font-semibold mb-4 text-slate-100">Event Inputs</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* TODO: Replace with <LocationInput /> component (latitude & longitude fields or geocoding) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm mb-1 text-gray-300">Latitude</label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  className="w-full rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 29.76"
                />
              </div>
              <div>
                <label className="block text-sm mb-1 text-gray-300">Longitude</label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  className="w-full rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., -95.36"
                />
              </div>
            </div>

            {/* TODO: Replace with <EventDatePicker /> component */}
            <div>
              <label className="block text-sm mb-1 text-gray-300">Event Date</label>
              <input
                type="date"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <button
              type="submit"
              className="inline-flex items-center px-5 py-2.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition disabled:opacity-50"
              disabled={loading}
            >
              {/* TODO: Show Loader spinner inside when loading */}
              Predict Rain Probability
            </button>
          </form>
        </section>

        <section className="p-6 rounded-lg bg-space-panel shadow-lg border border-slate-700">
          <h2 className="text-xl font-semibold mb-4 text-slate-100">Results</h2>
          {/* TODO: Conditional rendering rules:
                - If loading: show <Loader />
                - Else if error: show error message box
                - Else if result: show <ResultsDisplay data={result} />
                - Else: show placeholder text */}
          {!result && !loading && !error && (
            <p className="text-gray-400 text-sm">Submit event details to view a rain probability prediction.</p>
          )}
        </section>
      </main>

      <footer className="mt-16 text-center text-xs text-gray-500">
        <p>NASA Space Apps Challenge – Skeleton Build • {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

export default App;
