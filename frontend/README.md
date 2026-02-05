# Mamimind Frontend

Next.js frontend for Mamimind legal document intelligence platform.

## Features

- 📄 **Document Upload** - Drag & drop PDF upload with real-time progress
- 🔍 **Smart Search** - Natural language queries with AI-powered answers
- 📚 **Citations** - Every answer includes precise source citations
- 🎨 **Modern UI** - Clean, responsive interface built with Tailwind CSS
- ☁️ **Cloud Ready** - Optimized for GCP Cloud Run deployment

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **API Client**: Axios
- **Deployment**: Cloud Run (Docker)

## Local Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Edit .env.local with your API URL
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Start development server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
npm run type-check  # TypeScript type checking
```

## Deployment to Cloud Run

### Option 1: Using Deploy Script (Recommended)

```bash
# Set environment variables
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1
export API_BASE_URL=https://your-api-url.run.app

# Deploy
./deploy-cloudrun.sh
```

### Option 2: Manual Deployment

```bash
# Build Docker image
docker build -t gcr.io/PROJECT_ID/mamimind-frontend .

# Push to Container Registry
docker push gcr.io/PROJECT_ID/mamimind-frontend

# Deploy to Cloud Run
gcloud run deploy mamimind-frontend \
  --image gcr.io/PROJECT_ID/mamimind-frontend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars NEXT_PUBLIC_API_BASE_URL=https://your-api-url.run.app
```

### Option 3: Cloud Build (CI/CD)

Create `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/mamimind-frontend', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/mamimind-frontend']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'mamimind-frontend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/mamimind-frontend'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/mamimind-frontend'
```

Then:

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL | Yes |

**Note**: All `NEXT_PUBLIC_*` variables are embedded at build time.

## Project Structure

```
frontend/
├── pages/              # Next.js pages
│   ├── index.tsx       # Homepage
│   ├── upload.tsx      # Upload page
│   └── search.tsx      # Search page
├── components/         # React components
│   ├── Layout.tsx
│   ├── UploadBox.tsx
│   ├── SearchBox.tsx
│   ├── AnswerPanel.tsx
│   └── CitationList.tsx
├── lib/               # Utilities
│   ├── api.ts         # API client
│   └── store.ts       # State management
├── styles/            # Global styles
│   └── globals.css
└── public/            # Static assets
```

## Key Features

### 1. Document Upload

- Drag & drop interface
- PDF validation (type, size)
- Real-time upload progress
- Automatic OCR trigger
- Document status tracking

### 2. Search Interface

- Natural language queries
- Example query suggestions
- Document filtering
- Real-time results
- Confidence scores

### 3. Answer Display

- Markdown rendering
- Citation highlighting
- Confidence visualization
- Reasoning explanation
- Source attribution

## Performance Optimization

- **Standalone Output**: Minimal Docker image
- **Image Optimization**: Disabled for Cloud Run
- **Code Splitting**: Automatic with Next.js
- **CDN**: Use Cloud CDN for static assets
- **Caching**: Browser and server-side caching

## Troubleshooting

### Build Failures

```bash
# Clear cache and rebuild
rm -rf .next node_modules
npm install
npm run build
```

### API Connection Issues

1. Check `NEXT_PUBLIC_API_BASE_URL` is correct
2. Verify CORS settings on backend
3. Check network/firewall rules
4. Test API directly with curl

### Cloud Run Issues

```bash
# View logs
gcloud run services logs read mamimind-frontend --region=us-central1

# Check service status
gcloud run services describe mamimind-frontend --region=us-central1
```

## Security

- All API calls use HTTPS in production
- No sensitive data in frontend code
- Environment variables for configuration
- Content Security Policy headers
- XSS protection

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Create feature branch
2. Make changes
3. Test locally
4. Submit PR

## License

MIT
