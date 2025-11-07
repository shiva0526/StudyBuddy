import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Dashboard({ username, user }) {
  const [showCreatePlan, setShowCreatePlan] = useState(false)
  const [plans, setPlans] = useState([])
  const [progress, setProgress] = useState(null)
  const [formData, setFormData] = useState({
    subject: '',
    topics: '',
    exam_date: '',
    daily_minutes: 60,
    session_length: 45
  })
  const navigate = useNavigate()

  useEffect(() => {
    fetchProgress()
  }, [username])

  const fetchProgress = async () => {
    try {
      const response = await fetch(`/api/progress/${username}`)
      const data = await response.json()
      setProgress(data)
    } catch (error) {
      console.error('Error fetching progress:', error)
    }
  }

  const handleCreatePlan = async (e) => {
    e.preventDefault()
    
    try {
      const topics = formData.topics.split(',').map(t => t.trim()).filter(Boolean)
      
      const response = await fetch('/api/create_plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          subject: formData.subject,
          topics,
          exam_date: formData.exam_date,
          prefs: {
            daily_minutes: parseInt(formData.daily_minutes),
            session_length: parseInt(formData.session_length),
            preferred_times: ['morning', 'evening']
          }
        })
      })
      
      const data = await response.json()
      
      localStorage.setItem(`plan_${username}_${data.plan_id}`, JSON.stringify(data.plan))
      const existingPlans = JSON.parse(localStorage.getItem(`plans_${username}`) || '[]')
      existingPlans.push(data.plan)
      localStorage.setItem(`plans_${username}`, JSON.stringify(existingPlans))
      
      alert(`✓ ${data.summary}`)
      setShowCreatePlan(false)
      setFormData({ subject: '', topics: '', exam_date: '', daily_minutes: 60, session_length: 45 })
      navigate('/plan')
    } catch (error) {
      console.error('Error creating plan:', error)
      alert('Error creating plan')
    }
  }

  return (
    <div className="space-y-6">
      <div className="card bg-gradient-to-r from-primary to-purple-600 text-white">
        <h1 className="text-3xl font-bold mb-2">Welcome back, {user?.name || username}! 👋</h1>
        <p className="text-purple-100">Ready to ace your exams? Let's get studying!</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">Total XP</p>
              <p className="text-3xl font-bold text-primary">{progress?.xp || 0}</p>
            </div>
            <div className="text-4xl">⭐</div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">Level</p>
              <p className="text-3xl font-bold text-secondary">{progress?.level || 1}</p>
            </div>
            <div className="text-4xl">🏆</div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">Quizzes Taken</p>
              <p className="text-3xl font-bold text-accent">{progress?.total_quizzes || 0}</p>
            </div>
            <div className="text-4xl">📝</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <button
              onClick={() => setShowCreatePlan(true)}
              className="w-full btn-primary text-left flex items-center justify-between"
            >
              <span>📅 Create Study Plan</span>
              <span>→</span>
            </button>
            <button
              onClick={() => navigate('/upload')}
              className="w-full bg-secondary hover:bg-cyan-600 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-between"
            >
              <span>📤 Upload Resources</span>
              <span>→</span>
            </button>
            <button
              onClick={() => navigate('/revision')}
              className="w-full bg-accent hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-between"
            >
              <span>📚 Revision Hub</span>
              <span>→</span>
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold mb-4">Weak Topics</h2>
          {progress?.weak_topics?.length > 0 ? (
            <div className="space-y-2">
              {progress.weak_topics.slice(0, 5).map((topic, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                  <span className="text-sm text-red-800">{topic}</span>
                  <span className="text-red-400">⚠️</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No weak topics yet. Take some quizzes!</p>
          )}
        </div>
      </div>

      {showCreatePlan && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-6">Create Study Plan</h2>
            <form onSubmit={handleCreatePlan} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Subject</label>
                <input
                  type="text"
                  value={formData.subject}
                  onChange={(e) => setFormData({...formData, subject: e.target.value})}
                  className="input-field"
                  placeholder="e.g., Calculus, Biology, History"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Topics (comma-separated)</label>
                <textarea
                  value={formData.topics}
                  onChange={(e) => setFormData({...formData, topics: e.target.value})}
                  className="input-field"
                  rows="3"
                  placeholder="e.g., Integration, Derivatives, Limits"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Exam Date</label>
                <input
                  type="date"
                  value={formData.exam_date}
                  onChange={(e) => setFormData({...formData, exam_date: e.target.value})}
                  className="input-field"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Daily Minutes</label>
                  <input
                    type="number"
                    value={formData.daily_minutes}
                    onChange={(e) => setFormData({...formData, daily_minutes: e.target.value})}
                    className="input-field"
                    min="30"
                    max="300"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Session Length (min)</label>
                  <input
                    type="number"
                    value={formData.session_length}
                    onChange={(e) => setFormData({...formData, session_length: e.target.value})}
                    className="input-field"
                    min="15"
                    max="120"
                  />
                </div>
              </div>

              <div className="flex space-x-3 pt-4">
                <button type="submit" className="btn-primary flex-1">
                  Create Plan
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreatePlan(false)}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-2 px-6 rounded-lg flex-1"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
