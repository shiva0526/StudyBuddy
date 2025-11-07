# StudyBuddy - AI-Powered Study Platform

## Project Overview
StudyBuddy is a comprehensive web application that helps students create personalized study plans, learn with AI-powered tutoring, take adaptive quizzes, and prepare for exams with intelligent revision materials.

## Recent Changes (November 7, 2025)
- Complete project implementation with FastAPI backend and React frontend
- RAG (Retrieval Augmented Generation) pipeline for personalized learning
- Quiz engine with AI grading and gamification (XP, levels)
- Spaced repetition flashcard system using SM-2 algorithm
- Revision pack generator with short notes and flashcards
- YouTube video integration with transcript analysis
- Full CRUD operations for study plans, resources, and quizzes
- **NEW**: Enhanced LLM client with retry logic and structured output support
- **NEW**: Fixed OpenAI API compatibility by pinning httpx to 0.27.2
- **NEW**: Added health endpoint (/api/health) and comprehensive logging
- **NEW**: OpenAI API key integrated and working for real AI responses

## Architecture

### Backend (Python + FastAPI)
- **API Server**: FastAPI running on port 8000
- **Database**: Replit DB (key-value store)
- **AI Integration**: OpenAI GPT-4o-mini and text-embedding-3-small
- **RAG Pipeline**: PDF extraction → chunking → embedding → vector retrieval
- **Key Modules**:
  - `main.py`: API endpoints and routing
  - `llm_client.py`: OpenAI wrapper with mock mode fallback
  - `embeddings.py`: Vector operations and similarity search
  - `plan_generator.py`: Study schedule algorithm
  - `quiz.py`: Quiz generation and grading
  - `spaced_repetition.py`: SM-2 flashcard algorithm

### Frontend (React + Vite)
- **Dev Server**: Vite on port 5000 with proxy to backend
- **Routing**: React Router for multi-page navigation
- **Styling**: TailwindCSS with custom components
- **Pages**:
  - Dashboard: Overview, quick actions, stats
  - Upload: File upload with drag-drop
  - Plan: Study schedule calendar
  - Session: Learning with AI lessons and videos
  - RevisionHub: Generated study materials

### Data Flow
1. User uploads PDF → Extracted → Chunked → Embedded → Stored in DB
2. User creates plan → Topics analyzed → Sessions scheduled
3. User starts session → RAG retrieval → LLM generates lesson → Videos found
4. User takes quiz → LLM generates questions → Graded → XP earned → Weak topics tracked
5. User generates revision pack → LLM creates notes/flashcards → Exportable

## Key Features Implementation

### RAG (Retrieval Augmented Generation)
- Chunks documents into ~1000 character segments with 200 char overlap
- Creates OpenAI embeddings for each chunk
- Cosine similarity for top-k retrieval
- Context-aware LLM responses with citations

### Study Plan Algorithm
Uses weighted scoring:
- `alpha * past_paper_frequency + beta * note_size + gamma * baseline_difficulty`
- Distributes minutes across topics proportionally
- Creates sessions respecting daily limits and preferences

### Spaced Repetition (SM-2)
- Quality rating (0-5) adjusts easiness factor
- Interval calculation: 1 day → 6 days → easiness * previous interval
- Automatic scheduling of due reviews
- Failed cards reset to 1-day interval

### Quiz Engine
- LLM generates structured JSON with questions, choices, answers, explanations
- MCQ graded client-side for speed
- Short-answer questions use LLM grader
- Incorrect answers → flashcards for reinforcement

## Environment Variables
- `OPENAI_API_KEY`: Required for AI features (works in mock mode without)
- `YOUTUBE_API_KEY`: Optional for video search
- `DATABASE_URL`: Auto-configured by Replit

## Workflow Configuration
Single workflow runs both backend and frontend:
```bash
bash -c "python start_backend.py & cd frontend && npm run dev"
```
- Backend API: http://localhost:8000
- Frontend: http://localhost:5000 (webview)

## Mock Mode
When OPENAI_API_KEY is not set:
- Returns sample quiz questions
- Uses deterministic hash-based embeddings (1536-dim)
- Provides placeholder AI responses
- All features functional for testing

## File Structure
```
backend/         - Python FastAPI application
frontend/src/    - React components and pages
uploads/         - User-uploaded study materials
exports/         - Generated markdown exports
requirements.txt - Python dependencies
package.json     - Node dependencies (in frontend/)
```

## User Preferences
- Default study session: 45 minutes
- Default daily study time: 60 minutes
- All users start at Level 1 with 0 XP
- XP system: 10 XP per correct quiz answer, level up every 100 XP

## Development Notes
- LSP diagnostics present but non-blocking (mostly type hints)
- Frontend uses proxy for API calls (see vite.config.js)
- Replit DB fallback to in-memory dict if unavailable
- PDF extraction uses PyMuPDF (fitz)
- Vector similarity uses NumPy for efficiency

## Next Steps
- Set OPENAI_API_KEY in Secrets for full AI functionality
- Upload study materials to test RAG pipeline
- Create study plan to test scheduling algorithm
- Generate quizzes to test gamification
- Generate revision pack to test exports
