/**
 * Upload page - Document upload interface
 */

import React from 'react';
import { FileText, Clock, CheckCircle, XCircle } from 'lucide-react';
import UploadBox from '@/components/UploadBox';
import { useStore } from '@/lib/store';
import { formatDistanceToNow } from 'date-fns';

export default function UploadPage() {
  const { documents } = useStore();

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          Upload Legal Documents
        </h1>
        <p className="text-lg text-gray-600">
          Upload PDF documents to analyze and search
        </p>
      </div>

      {/* Upload Box */}
      <UploadBox />

      {/* Recent Uploads */}
      {documents.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              Recent Uploads
            </h2>
          </div>

          <div className="divide-y">
            {documents.slice(0, 10).map((doc) => (
              <DocumentRow key={doc.doc_id} document={doc} />
            ))}
          </div>
        </div>
      )}

      {/* Tips */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl p-6 border border-primary-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          💡 Tips for Best Results
        </h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>• Upload high-quality, text-based PDFs for accurate OCR</li>
          <li>• Document processing takes 1-3 minutes depending on size</li>
          <li>• You can upload multiple documents and search across all of them</li>
          <li>• Supported formats: PDF (max 50MB per file)</li>
        </ul>
      </div>
    </div>
  );
}

function DocumentRow({ document }: { document: any }) {
  const statusConfig = {
    uploaded: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100', label: 'Uploaded' },
    ocr_processing: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100', label: 'Processing' },
    ocr_completed: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100', label: 'OCR Done' },
    indexing: { icon: Clock, color: 'text-purple-500', bg: 'bg-purple-100', label: 'Indexing' },
    indexed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', label: 'Ready' },
    ready: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', label: 'Ready' },
    failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', label: 'Failed' },
  };

  const status = statusConfig[document.status as keyof typeof statusConfig] || statusConfig.uploaded;
  const StatusIcon = status.icon;

  return (
    <div className="px-6 py-4 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          <FileText className="h-10 w-10 text-gray-400 flex-shrink-0" />

          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 truncate">
              {document.metadata.filename}
            </h3>
            <div className="flex items-center space-x-3 mt-1">
              <span className="text-xs text-gray-500">
                {(document.metadata.file_size / 1024 / 1024).toFixed(2)} MB
              </span>
              {document.metadata.page_count && (
                <span className="text-xs text-gray-500">
                  {document.metadata.page_count} pages
                </span>
              )}
              <span className="text-xs text-gray-500">
                {formatDistanceToNow(new Date(document.created_at), { addSuffix: true })}
              </span>
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${status.bg}`}>
          <StatusIcon className={`h-4 w-4 ${status.color}`} />
          <span className={`text-xs font-medium ${status.color}`}>
            {status.label}
          </span>
        </div>
      </div>
    </div>
  );
}
