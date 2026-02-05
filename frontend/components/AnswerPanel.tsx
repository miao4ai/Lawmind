/**
 * Answer display panel with citations
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { CheckCircle, AlertCircle, Brain } from 'lucide-react';
import { QueryResult } from '@/lib/api';
import CitationList from './CitationList';

interface AnswerPanelProps {
  result: QueryResult;
}

export default function AnswerPanel({ result }: AnswerPanelProps) {
  const confidenceColor =
    result.confidence >= 0.8
      ? 'text-green-600'
      : result.confidence >= 0.6
      ? 'text-yellow-600'
      : 'text-red-600';

  const confidenceLabel =
    result.confidence >= 0.8
      ? 'High Confidence'
      : result.confidence >= 0.6
      ? 'Medium Confidence'
      : 'Low Confidence';

  return (
    <div className="space-y-6">
      {/* Answer Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-50 to-blue-50 px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white rounded-lg">
                <Brain className="h-5 w-5 text-primary-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Answer
                </h3>
                <p className="text-sm text-gray-600">{result.query}</p>
              </div>
            </div>

            {/* Confidence Badge */}
            <div
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${
                result.confidence >= 0.8
                  ? 'bg-green-100'
                  : result.confidence >= 0.6
                  ? 'bg-yellow-100'
                  : 'bg-red-100'
              }`}
            >
              {result.confidence >= 0.6 ? (
                <CheckCircle className={`h-4 w-4 ${confidenceColor}`} />
              ) : (
                <AlertCircle className={`h-4 w-4 ${confidenceColor}`} />
              )}
              <span className={`text-sm font-medium ${confidenceColor}`}>
                {confidenceLabel}
              </span>
            </div>
          </div>
        </div>

        {/* Answer Content */}
        <div className="px-6 py-5">
          <div className="prose max-w-none">
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="text-gray-800 leading-relaxed mb-4">
                    {children}
                  </p>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-gray-900">
                    {children}
                  </strong>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-inside space-y-2 mb-4">
                    {children}
                  </ul>
                ),
              }}
            >
              {result.answer}
            </ReactMarkdown>
          </div>

          {/* Confidence Score */}
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Confidence Score</span>
              <div className="flex items-center space-x-3">
                <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      result.confidence >= 0.8
                        ? 'bg-green-600'
                        : result.confidence >= 0.6
                        ? 'bg-yellow-600'
                        : 'bg-red-600'
                    }`}
                    style={{ width: `${result.confidence * 100}%` }}
                  />
                </div>
                <span className="font-mono font-medium">
                  {(result.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Reasoning (if available) */}
        {result.reasoning && (
          <div className="px-6 py-4 bg-gray-50 border-t">
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                View reasoning process
              </summary>
              <div className="mt-3 text-sm text-gray-600 whitespace-pre-wrap">
                {result.reasoning}
              </div>
            </details>
          </div>
        )}
      </div>

      {/* Citations */}
      {result.citations && result.citations.length > 0 && (
        <CitationList citations={result.citations} />
      )}
    </div>
  );
}
