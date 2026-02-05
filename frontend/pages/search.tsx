/**
 * Search page - Legal document Q&A interface
 */

import React, { useState } from 'react';
import { AlertCircle, FileText } from 'lucide-react';
import SearchBox from '@/components/SearchBox';
import AnswerPanel from '@/components/AnswerPanel';
import { api, QueryResult } from '@/lib/api';
import { useStore } from '@/lib/store';

export default function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { userId, selectedDocIds, documents, toggleDocument } = useStore();

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const queryResult = await api.query(
        userId,
        query,
        selectedDocIds.length > 0 ? selectedDocIds : undefined,
        5
      );

      setResult(queryResult);
    } catch (err: any) {
      console.error('Search error:', err);
      setError(
        err.response?.data?.error ||
        'Failed to search. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Filter ready documents
  const readyDocs = documents.filter((doc) =>
    ['ready', 'indexed'].includes(doc.status)
  );

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          Search Legal Documents
        </h1>
        <p className="text-lg text-gray-600">
          Ask questions about your documents in natural language
        </p>
      </div>

      {/* Document Filter */}
      {readyDocs.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Search in specific documents (optional):
          </h3>
          <div className="flex flex-wrap gap-2">
            {readyDocs.map((doc) => (
              <button
                key={doc.doc_id}
                onClick={() => toggleDocument(doc.doc_id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedDocIds.includes(doc.doc_id)
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <FileText className="inline h-4 w-4 mr-1" />
                {doc.metadata.filename}
              </button>
            ))}
          </div>
          {selectedDocIds.length > 0 && (
            <p className="text-xs text-gray-500 mt-2">
              Searching in {selectedDocIds.length} selected document(s)
            </p>
          )}
        </div>
      )}

      {/* Search Box */}
      <SearchBox onSearch={handleSearch} isLoading={isLoading} />

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-800">
              Search Failed
            </h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-primary-600 mb-4" />
          <p className="text-gray-600">Analyzing documents...</p>
        </div>
      )}

      {/* Results */}
      {!isLoading && result && <AnswerPanel result={result} />}

      {/* No Documents Warning */}
      {!isLoading && !result && readyDocs.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-center">
          <AlertCircle className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Documents Available
          </h3>
          <p className="text-gray-600 mb-4">
            Please upload some documents first before searching.
          </p>
          <a
            href="/upload"
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Upload Documents
          </a>
        </div>
      )}
    </div>
  );
}
