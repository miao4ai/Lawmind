/**
 * Search box component for legal document queries
 */

import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface SearchBoxProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export default function SearchBox({ onSearch, isLoading }: SearchBoxProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  // Example queries
  const exampleQueries = [
    'What are the termination conditions?',
    'Who is liable for damages?',
    'What are the payment terms?',
    'What is the confidentiality clause?',
  ];

  return (
    <div className="w-full">
      {/* Search Form */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your legal documents..."
            disabled={isLoading}
            className="w-full px-6 py-4 pr-14 text-lg border-2 border-gray-300 rounded-xl
                     focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200
                     disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary-600 text-white
                     rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed
                     transition-colors"
          >
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <Search className="h-6 w-6" />
            )}
          </button>
        </div>
      </form>

      {/* Example Queries */}
      <div className="mt-4">
        <p className="text-sm text-gray-600 mb-2">Try asking:</p>
        <div className="flex flex-wrap gap-2">
          {exampleQueries.map((example, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(example);
                onSearch(example);
              }}
              disabled={isLoading}
              className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-full
                       hover:border-primary-500 hover:bg-primary-50 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
