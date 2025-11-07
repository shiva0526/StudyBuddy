# StudyBuddy - AI-Powered Study Platform

## Project Overview
StudyBuddy is a comprehensive web application that helps students create personalized study plans, learn with AI-powered tutoring, take adaptive quizzes, and prepare for exams with intelligent revision materials.

## Recent Changes (November 7, 2025)
- **MAJOR**: Complete migration from in-memory storage to PostgreSQL for permanent data persistence
- **SECURITY**: Added ownership validation to all user-specific data endpoints
- Complete project implementation with FastAPI backend and React frontend
- RAG (Retrieval Augmented Generation) pipeline for personalized learning
- Quiz engine with AI grading and gamification (XP, levels)
- Spaced repetition flashcard system using SM-2 algorithm
- Revision pack generator with short notes and flashcards
- YouTube video integration with transcript analysis
- Full CRUD operations for study plans, resources, and quizzes with PostgreSQL
- Enhanced LLM client with retry logic and structured output support
- Fixed OpenAI API compatibility by pinning httpx to 0.27.2
- Added health endpoint (/api/health) and comprehensive logging
- OpenAI API key integrated and working for real AI responses

## Architecture

### Backend (Python + FastAPI)
- **API Server**: FastAPI running on port 8000
- **Database**: PostgreSQL (permanent data persistence)
- **AI Integration**: OpenAI GPT-4o-mini and text-embedding-3-small
- **RAG Pipeline**: PDF extraction → chunking → embedding → vector retrieval
- **Key Modules**:
  - `main.py`: API endpoints and routing with ownership validation
  - `db_client.py`: PostgreSQL client with comprehensive schema management
  - `llm_client.py`: OpenAI wrapper with mock mode fallback
  - `embeddings.py`: Vector operations, similarity search, and keyword fallback
  - `plan_generator.py`: Study schedule algorithm
  - `quiz.py`: Quiz generation and grading
  - `spaced_repetition.py`: SM-2 flashcard algorithm with PostgreSQL storage
  - `revision.py`: Revision pack generation with markdown export

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

## Database Schema (PostgreSQL)
Tables:
- **users**: User profiles, XP, level, streak, preferences
- **resources**: Uploaded study materials metadata
- **chunks**: Text chunks from resources with position tracking
- **embeddings**: Vector embeddings (1536-dim) for RAG retrieval
- **plans**: Study plans with sessions and scheduling
- **quizzes**: Generated quizzes with questions and answers
- **progress**: User progress tracking, weak topics, history
- **sr_cards**: Spaced repetition flashcards with SM-2 data
- **revision_packs**: Generated revision materials with export paths

All tables use proper foreign keys, constraints, and indices for data integrity.

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
- PostgreSQL database schema auto-initializes on startup
- PDF extraction uses PyMuPDF (fitz)
- Vector similarity uses NumPy for efficiency
- All user-specific endpoints enforce ownership validation for security
- **IMPORTANT**: New db_client getters must enforce username scoping at API layer

## Next Steps
- Set OPENAI_API_KEY in Secrets for full AI functionality
- Upload study materials to test RAG pipeline
- Create study plan to test scheduling algorithm
- Generate quizzes to test gamification
- Generate revision pack to test exports
