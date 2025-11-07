import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import ChatBox from '../components/ChatBox'
import QuizGame from '../components/QuizGame'

export default function Session({ username }) {
  const { sessionId } = useParams()
  const [sessionData, setSessionData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showQuiz, setShowQuiz] = useState(false)
  const [showChat, setShowChat] = useState(false)

  useEffect(() => {
    startSession()
  }, [sessionId])

  const startSession = async () => {
    try {
      const response = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, session_id: sessionId })
      })
      const data = await response.json()
      setSessionData(data)
      setLoading(false)
    } catch (error) {
      console.error('Error starting session:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin text-6xl mb-4">⚙️</div>
          <p className="text-gray-600">Loading session...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <div className="card">
          <h1 className="text-2xl font-bold mb-2">{sessionData?.topic || 'Study Session'}</h1>
          <p className="text-gray-600 mb-6">AI-generated lesson content</p>
          
          <div className="prose max-w-none">
            <div className="whitespace-pre-line text-gray-700">
              {sessionData?.lesson_content || 'No content available'}
            </div>
          </div>

          <div className="mt-6 flex space-x-3">
            <button onClick={() => setShowQuiz(true)} className="btn-primary">
              📝 Generate Quiz
            </button>
            <button onClick={() => setShowChat(true)} className="btn-secondary">
              💬 Ask Questions
            </button>
          </div>
        </div>

        {sessionData?.citations && sessionData.citations.length > 0 && (
          <div className="card">
            <h2 className="text-lg font-bold mb-3">📚 Sources Used</h2>
            <div className="space-y-2">
              {sessionData.citations.map((citation, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg text-sm">
                  <p className="text-gray-700">{citation.text}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Relevance: {(citation.score * 100).toFixed(0)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-6">
        {sessionData?.videos && sessionData.videos.length > 0 && (
          <div className="card">
            <h2 className="text-lg font-bold mb-3">🎥 Recommended Videos</h2>
            {sessionData.videos.map((video, idx) => (
              <div key={idx} className="mb-4">
                <a
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline font-semibold"
                >
                  {video.title}
                </a>
                <p className="text-xs text-gray-500 mt-1">{video.snippet?.slice(0, 100)}...</p>
              </div>
            ))}
          </div>
        )}

        <div className="card">
          <h2 className="text-lg font-bold mb-3">📊 Session Info</h2>
          <div className="space-y-2 text-sm">
            <p><strong>Resources Used:</strong> {sessionData?.resources_used || 0}</p>
            <p><strong>Session ID:</strong> {sessionId}</p>
          </div>
        </div>
      </div>

      {showQuiz && <QuizGame username={username} topic={sessionData?.topic} onClose={() => setShowQuiz(false)} />}
      {showChat && <ChatBox username={username} topic={sessionData?.topic} onClose={() => setShowChat(false)} />}
    </div>
  )
}
