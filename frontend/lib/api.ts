/**
 * API client for Mamimind backend services
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

// Types
export interface Document {
  doc_id: string;
  user_id: string;
  status: string;
  metadata: {
    filename: string;
    file_size: number;
    mime_type: string;
    page_count?: number;
  };
  created_at: string;
  updated_at: string;
}

export interface Citation {
  doc_id: string;
  chunk_id: string;
  text: string;
  page_number?: number;
  confidence: number;
}

export interface QueryResult {
  query: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  reasoning?: string;
  metadata?: Record<string, any>;
}

export interface UploadResponse {
  doc_id: string;
  upload_url: string;
  storage_path: string;
}

// API Client
class MamimindAPI {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 60000, // 60 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        throw error;
      }
    );
  }

  /**
   * Get signed upload URL for document
   */
  async getUploadUrl(
    userId: string,
    filename: string,
    fileSize: number,
    mimeType: string = 'application/pdf'
  ): Promise<UploadResponse> {
    const response = await this.client.post('/upload', {
      user_id: userId,
      filename,
      file_size: fileSize,
      mime_type: mimeType,
    });

    return response.data;
  }

  /**
   * Upload file to signed URL
   */
  async uploadFile(signedUrl: string, file: File): Promise<void> {
    await axios.put(signedUrl, file, {
      headers: {
        'Content-Type': file.type,
      },
    });
  }

  /**
   * Complete upload and trigger OCR
   */
  async completeUpload(docId: string): Promise<void> {
    await this.client.post(`/complete/${docId}`);
  }

  /**
   * Query documents with RAG
   */
  async query(
    userId: string,
    query: string,
    docIds?: string[],
    topK: number = 5
  ): Promise<QueryResult> {
    const response = await this.client.post('/query', {
      user_id: userId,
      query,
      doc_ids: docIds,
      top_k: topK,
    });

    return response.data.data;
  }

  /**
   * Get document status
   */
  async getDocumentStatus(docId: string): Promise<Document> {
    const response = await this.client.get(`/status/${docId}`);
    return response.data;
  }

  /**
   * List user documents
   */
  async listDocuments(userId: string): Promise<Document[]> {
    const response = await this.client.get(`/documents`, {
      params: { user_id: userId },
    });
    return response.data.documents || [];
  }
}

// Export singleton instance
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
export const api = new MamimindAPI(apiBaseUrl);

// Export for testing
export { MamimindAPI };
