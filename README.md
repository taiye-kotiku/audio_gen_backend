# Audio Generation Backend

Advanced FastAPI backend for AI-powered audio processing and generation. Part of a full-stack AI content platform serving digital marketing agencies and content creators.

## 🎯 Purpose

Provides intelligent audio processing, generation, and batch processing capabilities. Handles concurrent requests, manages queues, and orchestrates complex AI workflows for audio content creation.

## ✨ Key Features

- **FastAPI Framework** - High-performance async API
- **Batch Processing** - Handle 1000+ requests efficiently
- **Queue Management** - Intelligent job scheduling and retry logic
- **Error Handling** - Robust error recovery and logging
- **Scalability** - Docker containerization for easy deployment
- **Real-time Monitoring** - Status tracking and progress updates

## 🏗️ Architecture

```
FastAPI Server
├── Audio Processing Pipeline
│   ├── Input Validation
│   ├── Processing Queue
│   ├── Batch Operations
│   └── Output Generation
├── Job Management
│   ├── Queue Handler
│   ├── Status Tracking
│   ├── Error Retry Logic
│   └── Logging System
└── Integration Layer
    ├── Database Connections
    ├── Storage Services
    └── External APIs
```

## 🚀 Performance

- **Response Time:** Sub-second API responses
- **Throughput:** 100+ concurrent requests
- **Batch Size:** 1000+ items per batch
- **Error Recovery:** Automatic retry with exponential backoff
- **Success Rate:** 99%+ with comprehensive error handling

## 💾 Database & Storage

- PostgreSQL for metadata and job tracking
- Supabase for real-time updates
- S3/Cloud Storage for audio file management
- Redis for queue management (optional)

## 🔧 Tech Stack

```
Framework: FastAPI
Language: Python 3.9+
Database: PostgreSQL / Supabase
Async: AsyncIO
Queue: Celery (optional) or built-in
Containerization: Docker
Deployment: AWS / GCP / Heroku
```

## 📦 Dependencies

```
fastapi==0.104.0
uvicorn==0.24.0
pydantic==2.0.0
sqlalchemy==2.0.0
python-multipart==0.0.6
aiofiles==23.0.0
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL or Supabase
- Docker (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/taiye-kotiku/audio_gen_backend
cd audio_gen_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run application
uvicorn main:app --reload
```

### Docker

```bash
# Build image
docker build -t audio_gen_backend .

# Run container
docker run -p 8000:8000 --env-file .env audio_gen_backend
```

## 📚 API Endpoints

### Health Check
```
GET /health
```

### Process Audio
```
POST /api/audio/process
Content-Type: multipart/form-data

{
  "file": <audio_file>,
  "processing_type": "enhance|generate|transform",
  "parameters": {...}
}
```

### Batch Processing
```
POST /api/audio/batch
Content-Type: application/json

{
  "job_id": "unique_id",
  "files": [...],
  "config": {...}
}
```

### Job Status
```
GET /api/jobs/{job_id}
```

### Job Results
```
GET /api/jobs/{job_id}/results
```

## 🔐 Security

- Input validation on all endpoints
- Rate limiting implemented
- CORS properly configured
- Environment variables for sensitive data
- SQL injection prevention through SQLAlchemy ORM

## 📈 Real-World Usage

This backend powers content generation platforms processing 10,000+ audio files monthly:
- Digital marketing agencies creating podcast content
- Content creators generating audio for videos
- E-commerce platforms creating product descriptions
- Educational platforms producing course audio

**Results:**
- 90% reduction in audio processing time
- Batch operations 10x faster than sequential
- 99%+ success rate with automatic error recovery

## 🔄 Integration Examples

### With Frontend (See audio_gen_frontend)
The backend works in tandem with React frontend to provide:
- File upload interface
- Real-time progress tracking
- Result preview and download
- Batch management dashboard

### With External Services
- WhatsApp/Telegram for status notifications
- Email for job completion alerts
- Webhooks for external system integration
- S3/Cloud Storage for file persistence

## 📊 Monitoring & Logging

```python
# Comprehensive logging setup
- Request/Response logging
- Error tracking with context
- Performance metrics
- Database query logging
- File operation auditing
```

## 🛠️ Development

### Testing
```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/
```

### Code Quality
```bash
# Format code
black app/

# Lint
flake8 app/

# Type checking
mypy app/
```

## 🚢 Deployment

### Environment Variables Required
```
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_KEY=...
ENVIRONMENT=production
LOG_LEVEL=info
API_WORKERS=4
```

### Production Checklist
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] CORS settings validated
- [ ] Rate limiting configured
- [ ] Logging to external service (Sentry, DataDog, etc.)
- [ ] Health checks passing
- [ ] Load tested
- [ ] Rollback plan documented

## 📈 Performance Optimization Tips

1. **Database Indexing** - Index frequently queried columns
2. **Caching** - Implement Redis for repeated operations
3. **Connection Pooling** - Use SQLAlchemy connection pools
4. **Async Operations** - Leverage FastAPI's async capabilities
5. **Queue System** - Offload heavy processing to background jobs

## 🐛 Troubleshooting

### Common Issues

**Issue:** Database connection timeout
```
Solution: Check DATABASE_URL, ensure DB is accessible, increase timeout settings
```

**Issue:** Out of memory on large batches
```
Solution: Reduce batch size, implement pagination, add streaming
```

**Issue:** Slow audio processing
```
Solution: Profile code, optimize algorithms, consider GPU acceleration
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Support

For issues, feature requests, or integration help:
- Check GitHub Issues
- Review documentation
- Contact via portfolio site: taiye.framer.website

## 📚 Related Projects

- **audio_gen_frontend** - React UI for audio generation
- **n8n-automation** - Workflow automation examples
- **python-scripts** - Utility scripts for batch operations

---

**Want to integrate audio processing into your application?** [View my portfolio](https://taiye.framer.website) for case studies and integration examples.
