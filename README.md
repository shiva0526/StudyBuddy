# StudyBuddy 📚

An AI-powered study platform that helps students plan their study schedule, learn with RAG-based tutoring, take adaptive quizzes, and prepare for exams with personalized revision packs.

## Features

- **🎯 Personalized Study Plans**: AI generates optimal study schedules based on exam dates and topics
- **📤 Smart Resource Upload**: Upload PDFs and text files that are automatically indexed for AI-powered learning
- **🤖 RAG-Powered Q&A**: Ask questions about your study materials and get AI answers with citations
- **📝 Adaptive Quiz Engine**: Generate quizzes on any topic with immediate AI grading and feedback
- **🎮 Gamified Learning**: Earn XP, level up, and track your progress with streaks
- **🃏 Spaced Repetition**: SM-2 algorithm for optimal flashcard review scheduling
- **📚 Revision Packs**: AI-generated exam preparation materials with short notes and flashcards
- **🎥 YouTube Integration**: Find and rank relevant educational videos for each topic
- **📊 Progress Analytics**: Track weak topics, quiz performance, and learning stats

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **OpenAI API**: LLM (GPT-4o-mini) and embeddings (text-embedding-3-small)
- **PyMuPDF**: PDF text extraction
- **Replit DB**: Key-value database for persistence
- **NumPy**: Vector similarity calculations for RAG

### Frontend
- **React 18**: Component-based UI
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first styling
- **React Router**: Multi-page navigation

## Setup Instructions

### 1. Set Required Secrets

Before running the app, set these secrets in Replit Secrets:

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

**Optional:**
- `YOUTUBE_API_KEY` - Google Data API key for YouTube search ([Get one here](https://console.cloud.google.com/apis/credentials))

### 2. Run the Application

Click the **Run** button or execute:

```bash
bash start.sh
```

This starts both the backend API (port 8000) and frontend dev server (port 5000).

### 3. Access the App

- **Frontend**: The webview will automatically open at port 5000
- **API Docs**: Visit `http://localhost:8000/docs` for the FastAPI interactive documentation

## Usage Guide

### Getting Started

1. **Create a User**: The app auto-creates a user profile with username `demo_user`

2. **Create a Study Plan**:
   - Go to Dashboard
   - Click "Create Study Plan"
   - Enter subject, topics (comma-separated), exam date, and study preferences
   - The AI will generate an optimal schedule with sessions spread across available days

3. **Upload Study Materials**:
   - Navigate to Upload page
   - Upload PDF notes or text files
   - The app automatically:
     - Extracts text
     - Chunks content (~1000 chars per chunk)
     - Creates embeddings
     - Stores in vector database for RAG

4. **Start a Learning Session**:
   - Go to Study Plan
   - Click "Start" on any session
   - Get AI-generated lesson with:
     - Topic summary
     - Examples and practice problems
     - Related YouTube videos
     - Citations from your materials

5. **Take Quizzes**:
   - In a session, click "Generate Quiz"
   - Answer MCQ questions
   - Get immediate feedback and XP
   - Incorrect answers become flashcards

6. **Generate Revision Pack**:
   - Go to Revision Hub
   - Click "Generate Revision Pack"
   - Get AI-generated:
     - Short notes on key concepts
     - Flashcards (Q&A format)
     - Memory aids and mnemonics
   - Download as Markdown

### API Endpoints

Key endpoints (see `/docs` for full API documentation):

- `GET /api/user/{username}` - Get or create user profile
- `POST /api/create_plan` - Generate study plan
- `POST /api/upload_resource` - Upload and index files
- `POST /api/session/start` - Start learning session
- `POST /api/rag_query` - Ask questions with RAG
- `POST /api/generate_quiz` - Create quiz
- `POST /api/submit_quiz` - Grade quiz and earn XP
- `POST /api/generate_revision_pack` - Create revision materials
- `GET /api/progress/{username}` - Get analytics

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI application & routes
│   ├── db_client.py         # Replit DB interface
│   ├── llm_client.py        # OpenAI API wrapper
│   ├── extract.py           # PDF/text extraction
│   ├── chunk.py             # Text chunking
│   ├── embeddings.py        # Vector embeddings & retrieval
│   ├── rag.py               # RAG query pipeline
│   ├── plan_generator.py    # Study plan algorithm
│   ├── quiz.py              # Quiz generation & grading
│   ├── revision.py          # Revision pack creation
│   ├── videos.py            # YouTube integration
│   └── spaced_repetition.py # SM-2 flashcard algorithm
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app component
│   │   ├── pages/           # Page components
│   │   └── components/      # Reusable components
│   ├── package.json         # Dependencies
│   └── vite.config.js       # Vite configuration
├── uploads/                 # Uploaded files
├── exports/                 # Generated exports
├── requirements.txt         # Python dependencies
└── README.md
```

## Data Models

Data is stored in Replit DB with these key patterns:

- `user:{username}` - User profile, XP, level, preferences
- `plan:{username}:{plan_id}` - Study plans with sessions
- `resource:{resource_id}` - Uploaded file metadata
- `chunk:{resource_id}:{chunk_id}` - Text chunks
- `embed:{resource_id}:{chunk_id}` - Vector embeddings
- `quiz:{username}:{quiz_id}` - Quiz data and results
- `progress:{username}` - Learning analytics
- `sr:{username}:{card_id}` - Spaced repetition cards
- `revision_pack:{username}:{id}` - Generated revision materials

## Mock Mode

If `OPENAI_API_KEY` is not set, the app runs in **mock mode**:
- Returns placeholder AI responses
- Uses deterministic hash-based embeddings
- All features work for testing, but with sample data

This allows you to test the UI and workflow without API costs.

## Development

### Backend Only
```bash
python start_backend.py
# API runs on http://localhost:8000
```

### Frontend Only
```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:5000
```

### Build for Production
```bash
cd frontend
npm run build
# Outputs to frontend/dist/
```

## Features Roadmap

Current MVP includes:
- ✅ Study plan generation
- ✅ RAG-powered learning sessions
- ✅ Quiz engine with grading
- ✅ Spaced repetition flashcards
- ✅ Revision pack generation
- ✅ Progress tracking
- ✅ YouTube video integration

Future enhancements:
- 📱 Mobile-optimized PWA
- 👥 Collaborative study groups
- 📅 Calendar sync
- 📊 Advanced analytics with predictions
- 🔔 Notification system
- 🌐 Multi-language support

## Troubleshooting

### Frontend not loading?
- Check that port 5000 is accessible
- Restart the workflow
- Check browser console for errors

### Backend errors?
- Verify `OPENAI_API_KEY` is set (or accept mock mode)
- Check `/tmp/logs/StudyBuddy_*.log` for errors
- Ensure Python dependencies are installed

### Upload not working?
- Check file format (PDF or TXT only)
- Verify uploads/ directory exists and is writable
- Check backend logs for extraction errors

## Credits

Built with:
- [OpenAI](https://openai.com) for LLM and embeddings
- [FastAPI](https://fastapi.tiangolo.com) for the backend
- [React](https://react.dev) + [Vite](https://vitejs.dev) for the frontend
- [TailwindCSS](https://tailwindcss.com) for styling
- [PyMuPDF](https://pymupdf.readthedocs.io) for PDF processing

## License

MIT License - feel free to use and modify for your own projects!

---

**Happy Studying! 🎓**
