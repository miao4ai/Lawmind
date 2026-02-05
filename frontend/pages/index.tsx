/**
 * Homepage - Landing page with feature overview
 */

import React from 'react';
import Link from 'next/link';
import { Search, Upload, FileText, Brain, CheckCircle } from 'lucide-react';

export default function Home() {
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Legal Document Intelligence
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Upload your legal documents and ask questions. Get instant answers with precise citations powered by AI.
        </p>

        <div className="flex justify-center space-x-4">
          <Link
            href="/upload"
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700
                     transition-colors font-medium flex items-center space-x-2"
          >
            <Upload className="h-5 w-5" />
            <span>Upload Document</span>
          </Link>

          <Link
            href="/search"
            className="px-6 py-3 bg-white text-gray-700 border-2 border-gray-300 rounded-lg
                     hover:border-primary-500 transition-colors font-medium flex items-center space-x-2"
          >
            <Search className="h-5 w-5" />
            <span>Search Documents</span>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="grid md:grid-cols-3 gap-8">
        <FeatureCard
          icon={<Upload className="h-8 w-8" />}
          title="Easy Upload"
          description="Drag and drop your PDF documents. We'll automatically extract and index the content."
          color="blue"
        />

        <FeatureCard
          icon={<Brain className="h-8 w-8" />}
          title="AI-Powered Search"
          description="Ask questions in natural language. Our AI understands legal context and reasoning."
          color="purple"
        />

        <FeatureCard
          icon={<FileText className="h-8 w-8" />}
          title="Precise Citations"
          description="Every answer comes with exact page references and confidence scores."
          color="green"
        />
      </section>

      {/* How it Works */}
      <section className="bg-white rounded-2xl shadow-sm border p-8">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
          How It Works
        </h2>

        <div className="grid md:grid-cols-4 gap-6">
          <Step
            number={1}
            title="Upload"
            description="Upload your legal documents (contracts, agreements, policies)"
          />
          <Step
            number={2}
            title="Process"
            description="Our AI extracts text and understands document structure"
          />
          <Step
            number={3}
            title="Ask"
            description="Ask questions about your documents in natural language"
          />
          <Step
            number={4}
            title="Get Answers"
            description="Receive accurate answers with citations and confidence scores"
          />
        </div>
      </section>

      {/* Use Cases */}
      <section>
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
          Perfect For
        </h2>

        <div className="grid md:grid-cols-2 gap-6">
          <UseCaseCard
            title="Legal Professionals"
            points={[
              'Quick contract review',
              'Find specific clauses',
              'Compare terms across documents',
            ]}
          />

          <UseCaseCard
            title="Business Teams"
            points={[
              'Understand legal agreements',
              'Extract key obligations',
              'Identify risks and liabilities',
            ]}
          />

          <UseCaseCard
            title="Compliance Officers"
            points={[
              'Audit policy documents',
              'Verify compliance requirements',
              'Track regulatory changes',
            ]}
          />

          <UseCaseCard
            title="Researchers"
            points={[
              'Analyze legal precedents',
              'Extract case information',
              'Build knowledge bases',
            ]}
          />
        </div>
      </section>
    </div>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  color: 'blue' | 'purple' | 'green';
}

function FeatureCard({ icon, title, description, color }: FeatureCardProps) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    green: 'bg-green-100 text-green-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 hover:shadow-md transition-shadow">
      <div className={`inline-flex p-3 rounded-lg ${colorClasses[color]} mb-4`}>
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

interface StepProps {
  number: number;
  title: string;
  description: string;
}

function Step({ number, title, description }: StepProps) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full
                    bg-primary-600 text-white font-bold text-lg mb-4">
        {number}
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}

interface UseCaseCardProps {
  title: string;
  points: string[];
}

function UseCaseCard({ title, points }: UseCaseCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4">{title}</h3>
      <ul className="space-y-3">
        {points.map((point, idx) => (
          <li key={idx} className="flex items-start space-x-3">
            <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
            <span className="text-gray-700">{point}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
