/**
 * Global state management with Zustand
 */

import { create } from 'zustand';
import { Document } from './api';

interface AppState {
  // User
  userId: string;
  setUserId: (userId: string) => void;

  // Documents
  documents: Document[];
  setDocuments: (documents: Document[]) => void;
  addDocument: (document: Document) => void;

  // Selected documents for search
  selectedDocIds: string[];
  toggleDocument: (docId: string) => void;
  clearSelection: () => void;
}

export const useStore = create<AppState>((set) => ({
  // User
  userId: 'demo_user', // In production, get from auth
  setUserId: (userId) => set({ userId }),

  // Documents
  documents: [],
  setDocuments: (documents) => set({ documents }),
  addDocument: (document) =>
    set((state) => ({ documents: [document, ...state.documents] })),

  // Selected documents
  selectedDocIds: [],
  toggleDocument: (docId) =>
    set((state) => ({
      selectedDocIds: state.selectedDocIds.includes(docId)
        ? state.selectedDocIds.filter((id) => id !== docId)
        : [...state.selectedDocIds, docId],
    })),
  clearSelection: () => set({ selectedDocIds: [] }),
}));
