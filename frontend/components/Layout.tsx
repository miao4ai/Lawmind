/**
 * Main layout component
 */

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FileText, Search, Upload } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const router = useRouter();

  const isActive = (path: string) => router.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center space-x-2">
              <FileText className="h-8 w-8 text-primary-600" />
              <span className="text-2xl font-bold text-gray-900">
                Mamimind
              </span>
            </Link>

            {/* Navigation */}
            <nav className="flex space-x-4">
              <Link
                href="/search"
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  isActive('/search')
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Search className="h-5 w-5" />
                <span className="font-medium">Search</span>
              </Link>

              <Link
                href="/upload"
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  isActive('/upload')
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Upload className="h-5 w-5" />
                <span className="font-medium">Upload</span>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-500 text-sm">
            © 2024 Mamimind - Legal Document Intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}
