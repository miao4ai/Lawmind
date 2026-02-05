/**
 * Document upload component with drag & drop
 */

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useStore } from '@/lib/store';

interface UploadState {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  message: string;
  docId?: string;
}

export default function UploadBox() {
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
    message: '',
  });

  const { userId, addDocument } = useStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];

      // Validate file
      if (!file.type.includes('pdf')) {
        setUploadState({
          status: 'error',
          progress: 0,
          message: 'Only PDF files are supported',
        });
        return;
      }

      if (file.size > 50 * 1024 * 1024) {
        // 50MB limit
        setUploadState({
          status: 'error',
          progress: 0,
          message: 'File size must be less than 50MB',
        });
        return;
      }

      try {
        setUploadState({
          status: 'uploading',
          progress: 10,
          message: 'Getting upload URL...',
        });

        // Step 1: Get signed upload URL
        const uploadData = await api.getUploadUrl(
          userId,
          file.name,
          file.size,
          file.type
        );

        setUploadState({
          status: 'uploading',
          progress: 30,
          message: 'Uploading file...',
        });

        // Step 2: Upload file to Cloud Storage
        await api.uploadFile(uploadData.upload_url, file);

        setUploadState({
          status: 'uploading',
          progress: 70,
          message: 'Processing document...',
        });

        // Step 3: Complete upload (triggers OCR)
        await api.completeUpload(uploadData.doc_id);

        setUploadState({
          status: 'uploading',
          progress: 90,
          message: 'Starting OCR...',
        });

        // Add to documents list
        addDocument({
          doc_id: uploadData.doc_id,
          user_id: userId,
          status: 'ocr_processing',
          metadata: {
            filename: file.name,
            file_size: file.size,
            mime_type: file.type,
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });

        setUploadState({
          status: 'success',
          progress: 100,
          message: 'Upload successful! Processing in background.',
          docId: uploadData.doc_id,
        });

        // Reset after 3 seconds
        setTimeout(() => {
          setUploadState({
            status: 'idle',
            progress: 0,
            message: '',
          });
        }, 3000);
      } catch (error: any) {
        console.error('Upload error:', error);
        setUploadState({
          status: 'error',
          progress: 0,
          message: error.response?.data?.error || 'Upload failed. Please try again.',
        });
      }
    },
    [userId, addDocument]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    multiple: false,
  });

  return (
    <div className="w-full">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-all duration-200
          ${
            isDragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-primary-400 bg-white'
          }
          ${uploadState.status === 'uploading' ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />

        {uploadState.status === 'idle' && (
          <>
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              {isDragActive ? 'Drop your PDF here' : 'Upload Legal Document'}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Drag and drop a PDF file, or click to browse
            </p>
            <p className="text-xs text-gray-400">
              Maximum file size: 50MB
            </p>
          </>
        )}

        {uploadState.status === 'uploading' && (
          <>
            <Loader2 className="mx-auto h-12 w-12 text-primary-600 animate-spin mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              {uploadState.message}
            </p>
            <div className="w-full max-w-xs mx-auto mt-4">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-600 transition-all duration-300"
                  style={{ width: `${uploadState.progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {uploadState.progress}%
              </p>
            </div>
          </>
        )}

        {uploadState.status === 'success' && (
          <>
            <CheckCircle className="mx-auto h-12 w-12 text-green-600 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              Upload Successful!
            </p>
            <p className="text-sm text-gray-500">
              {uploadState.message}
            </p>
            {uploadState.docId && (
              <p className="text-xs text-gray-400 mt-2 font-mono">
                Document ID: {uploadState.docId}
              </p>
            )}
          </>
        )}

        {uploadState.status === 'error' && (
          <>
            <XCircle className="mx-auto h-12 w-12 text-red-600 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              Upload Failed
            </p>
            <p className="text-sm text-red-600">{uploadState.message}</p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setUploadState({ status: 'idle', progress: 0, message: '' });
              }}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Try Again
            </button>
          </>
        )}
      </div>

      {/* Instructions */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">
          📄 Supported Documents
        </h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Legal contracts and agreements</li>
          <li>• Court documents and filings</li>
          <li>• Policy documents</li>
          <li>• Any PDF with legal text</li>
        </ul>
      </div>
    </div>
  );
}
