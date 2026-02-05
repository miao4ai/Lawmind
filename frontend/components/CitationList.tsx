/**
 * Citations list component
 */

import React from 'react';
import { FileText, ChevronDown } from 'lucide-react';
import { Citation } from '@/lib/api';

interface CitationListProps {
  citations: Citation[];
}

export default function CitationList({ citations }: CitationListProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gray-50 border-b">
        <h3 className="text-lg font-semibold text-gray-900">
          📚 Sources & Citations
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          {citations.length} relevant {citations.length === 1 ? 'passage' : 'passages'} found
        </p>
      </div>

      {/* Citations */}
      <div className="divide-y">
        {citations.map((citation, idx) => (
          <CitationCard key={citation.chunk_id} citation={citation} index={idx} />
        ))}
      </div>
    </div>
  );
}

interface CitationCardProps {
  citation: Citation;
  index: number;
}

function CitationCard({ citation, index }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(index === 0); // First citation expanded by default

  return (
    <div className="px-6 py-4 hover:bg-gray-50 transition-colors">
      {/* Citation Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-start justify-between text-left"
      >
        <div className="flex items-start space-x-3 flex-1">
          <div className="flex-shrink-0 mt-1">
            <div className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold">
              {index + 1}
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <span className="text-sm font-medium text-gray-900 truncate">
                Document {citation.doc_id.slice(0, 8)}
              </span>
              {citation.page_number && (
                <span className="text-xs text-gray-500">
                  Page {citation.page_number}
                </span>
              )}
            </div>

            {/* Preview (when collapsed) */}
            {!isExpanded && (
              <p className="text-sm text-gray-600 line-clamp-2">
                {citation.text}
              </p>
            )}
          </div>

          {/* Confidence Badge */}
          <div className="flex-shrink-0 flex items-center space-x-2">
            <div
              className={`px-2 py-1 rounded text-xs font-medium ${
                citation.confidence >= 0.8
                  ? 'bg-green-100 text-green-700'
                  : citation.confidence >= 0.6
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {(citation.confidence * 100).toFixed(0)}%
            </div>
            <ChevronDown
              className={`h-5 w-5 text-gray-400 transition-transform ${
                isExpanded ? 'transform rotate-180' : ''
              }`}
            />
          </div>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-3 ml-9">
          <div className="bg-gray-50 rounded-lg p-4 border-l-4 border-primary-500">
            <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
              {citation.text}
            </p>
          </div>

          {/* Metadata */}
          <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500">
            <span className="font-mono">ID: {citation.chunk_id}</span>
            <span>Relevance: {(citation.confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
