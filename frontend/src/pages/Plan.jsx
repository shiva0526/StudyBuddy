import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Plan({ username }) {
  const [isCreating, setIsCreating] = useState(false)
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [showImportantQuestions, setShowImportantQuestions] = useState(false)
  
  const [formData, setFormData] = useState({
    subject: '',
    examDate: '',
    dailyMinutes: 60,
    sessionLength: 45
  })
  
  const [topics, setTopics] = useState([])
  const [topicInput, setTopicInput] = useState('')
  const [files, setFiles] = useState([])
  const [csvFile, setCsvFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const navigate = useNavigate()

  useEffect(() => {
    fetchPlans()
  }, [username])

  const fetchPlans = async () => {
    try {
      const response = await fetch(`/api/plans/${username}`)
      if (response.ok) {
        const data = await response.json()
        setPlans(data)
        if (data.length > 0) {
          fetchPlanDetails(data[0].plan_id)
        }
      }
    } catch (err) {
      console.error('Error fetching plans:', err)
    }
  }

  const fetchPlanDetails = async (planId) => {
    try {
      const response = await fetch(`/api/plan/${username}/${planId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedPlan(data)
      }
    } catch (err) {
      console.error('Error fetching plan details:', err)
    }
  }

  const addTopic = () => {
    if (topicInput.trim()) {
      setTopics([...topics, topicInput.trim()])
      setTopicInput('')
    }
  }

  const removeTopic = (index) => {
    setTopics(topics.filter((_, i) => i !== index))
  }

  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files)
    setFiles([...files, ...newFiles])
  }

  const handleCsvChange = (e) => {
    if (e.target.files[0]) {
      setCsvFile(e.target.files[0])
    }
  }

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const newFiles = Array.from(e.dataTransfer.files)
    setFiles([...files, ...newFiles])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const formDataToSend = new FormData()
      formDataToSend.append('username', username)
      formDataToSend.append('subject', formData.subject)
      formDataToSend.append('exam_date', formData.examDate)
      formDataToSend.append('prefs', JSON.stringify({
        daily_minutes: formData.dailyMinutes,
        session_length: formData.sessionLength
      }))
      
      formDataToSend.append('topics_text', topics.join('\n'))
      
      if (csvFile) {
        formDataToSend.append('topics_csv', csvFile)
      }
      
      files.forEach(file => {
        formDataToSend.append('files', file)
      })

      const response = await fetch('/api/create_plan', {
        method: 'POST',
        body: formDataToSend
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create plan')
      }

      const result = await response.json()
      
      setIsCreating(false)
      
      fetchPlanDetails(result.plan_id)
      fetchPlans()
      
      setFormData({ subject: '', examDate: '', dailyMinutes: 60, sessionLength: 45 })
      setTopics([])
      setFiles([])
      setCsvFile(null)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const groupSessionsByDate = (sessions) => {
    const grouped = {}
    sessions.forEach(session => {
      const date = new Date(session.date).toLocaleDateString()
      if (!grouped[date]) {
        grouped[date] = []
      }
      grouped[date].push(session)
    })
    return grouped
  }

  if (isCreating) {
    return (
      <div className="space-y-6">
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold">📝 Create Study Plan</h1>
            <button
              className="text-sm text-gray-600 hover:text-gray-800"
              onClick={() => setIsCreating(false)}
            >
              ← Back to Plans
            </button>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold mb-2">Subject</label>
                <input
                  type="text"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  value={formData.subject}
                  onChange={(e) => setFormData({...formData, subject: e.target.value})}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Exam Date</label>
                <input
                  type="date"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  value={formData.examDate}
                  onChange={(e) => setFormData({...formData, examDate: e.target.value})}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-2">Topics</label>
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Add a topic..."
                    value={topicInput}
                    onChange={(e) => setTopicInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTopic())}
                  />
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={addTopic}
                  >
                    Add Topic
                  </button>
                </div>

                {topics.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {topics.map((topic, index) => (
                      <div key={index} className="bg-primary bg-opacity-10 px-3 py-1 rounded-full flex items-center gap-2">
                        <span className="text-sm">{topic}</span>
                        <button
                          type="button"
                          onClick={() => removeTopic(index)}
                          className="text-red-600 hover:text-red-800 font-bold"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div>
                  <label className="text-sm text-gray-600">OR Upload CSV:</label>
                  <input
                    type="file"
                    accept=".csv,.txt"
                    onChange={handleCsvChange}
                    className="block mt-2 text-sm text-gray-600"
                  />
                  {csvFile && <p className="text-sm text-green-600 mt-1">✓ {csvFile.name}</p>}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-2">Attach Files (Notes & Past Papers)</label>
              <div
                className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-primary transition-colors"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
              >
                <input
                  type="file"
                  multiple
                  accept=".pdf,.txt,.md,.png,.jpg"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <p className="text-gray-600">Drag & drop files here or click to browse</p>
                  <p className="text-sm text-gray-400 mt-1">PDF, TXT, MD, PNG, JPG</p>
                </label>
              </div>

              {files.length > 0 && (
                <div className="mt-3 space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                      <span className="text-sm">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold mb-2">Daily Study Minutes</label>
                <input
                  type="number"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  value={formData.dailyMinutes}
                  onChange={(e) => setFormData({...formData, dailyMinutes: parseInt(e.target.value)})}
                  min="15"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Session Length (minutes)</label>
                <input
                  type="number"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  value={formData.sessionLength}
                  onChange={(e) => setFormData({...formData, sessionLength: parseInt(e.target.value)})}
                  min="15"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full btn-primary py-3 text-lg"
              disabled={loading || (topics.length === 0 && !csvFile)}
            >
              {loading ? 'Creating Plan & Indexing Resources...' : '🚀 Create Plan & Index Resources'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">📅 Study Plan</h1>
          <button
            className="btn-primary"
            onClick={() => setIsCreating(true)}
          >
            + Create New Plan
          </button>
        </div>

        {selectedPlan ? (
          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold">{selectedPlan.subject}</h2>
              <p className="text-gray-600">
                Exam Date: {new Date(selectedPlan.exam_date).toLocaleDateString()} 
                {selectedPlan.meta && (
                  <>
                    {' • '}
                    {selectedPlan.meta.total_sessions} sessions
                  </>
                )}
              </p>
            </div>
            
            {selectedPlan.meta && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-primary bg-opacity-10 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Days Until Exam</p>
                  <p className="text-2xl font-bold text-primary">{selectedPlan.meta.days_until_exam}</p>
                </div>
                <div className="bg-secondary bg-opacity-10 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Total Sessions</p>
                  <p className="text-2xl font-bold text-secondary">{selectedPlan.meta.total_sessions}</p>
                </div>
                <div className="bg-accent bg-opacity-10 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Study Hours</p>
                  <p className="text-2xl font-bold text-accent">{selectedPlan.meta.total_study_hours}</p>
                </div>
              </div>
            )}

            {selectedPlan.important_questions && selectedPlan.important_questions.length > 0 && (
              <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-yellow-900">⭐ Important Questions Preview</h3>
                  <button
                    className="text-sm text-yellow-700 hover:text-yellow-900 font-semibold"
                    onClick={() => setShowImportantQuestions(true)}
                  >
                    View All →
                  </button>
                </div>
                <div className="mt-3 space-y-2">
                  {selectedPlan.important_questions.slice(0, 3).map((q, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="font-semibold">{q.topic}:</span> {q.stem}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500">No study plan created yet. Click Create New Plan to get started!</p>
        )}
      </div>

      {selectedPlan && selectedPlan.sessions && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Session Schedule</h2>
          <div className="space-y-6">
            {Object.entries(groupSessionsByDate(selectedPlan.sessions)).map(([date, sessions]) => (
              <div key={date}>
                <h3 className="text-lg font-semibold mb-3 text-gray-700">{date}</h3>
                <div className="space-y-3">
                  {sessions.map((session) => (
                    <div
                      key={session.id}
                      className="flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg hover:shadow-md transition-all cursor-pointer"
                      onClick={() => navigate(`/session/${session.id}`)}
                    >
                      <div className="flex-1">
                        <h4 className="font-semibold text-lg">{session.topic}</h4>
                        <p className="text-sm text-gray-600">{session.objective}</p>
                        <p className="text-xs text-gray-500 mt-1">{session.duration_min} minutes</p>
                      </div>
                      <div className="flex items-center space-x-3">
                        {session.status === 'completed' ? (
                          <span className="bg-green-100 text-green-800 text-sm font-semibold px-3 py-1 rounded-full">
                            ✓ Done
                          </span>
                        ) : (
                          <button className="btn-primary text-sm">Start →</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showImportantQuestions && selectedPlan && (
        <ImportantQuestionsModal
          planId={selectedPlan.plan_id || 'unknown'}
          username={username}
          onClose={() => setShowImportantQuestions(false)}
        />
      )}
    </div>
  )
}

function ImportantQuestionsModal({ planId, username, onClose }) {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchImportantQuestions()
  }, [])

  const fetchImportantQuestions = async () => {
    try {
      const response = await fetch(`/api/plan/${username}/${planId}/important_questions`)
      if (response.ok) {
        const data = await response.json()
        setQuestions(data.important_questions || [])
      }
    } catch (err) {
      console.error('Error fetching important questions:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-y-auto p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">⭐ Important Questions</h2>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-800 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className="space-y-4">
            {questions.map((q, idx) => (
              <div key={idx} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-sm font-semibold text-primary">{q.topic}</span>
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    Score: {q.importance_score}
                  </span>
                </div>
                <p className="font-medium mb-2">{q.stem}</p>
                {q.reason && <p className="text-sm text-gray-600 italic">{q.reason}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
