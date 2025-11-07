import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Plan({ username }) {
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const savedPlans = localStorage.getItem(`plans_${username}`)
    if (savedPlans) {
      const parsed = JSON.parse(savedPlans)
      setPlans(Array.isArray(parsed) ? parsed : [])
      if (parsed.length > 0) {
        setSelectedPlan(parsed[0])
      }
    }
  }, [username])

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

  return (
    <div className="space-y-6">
      <div className="card">
        <h1 className="text-2xl font-bold mb-4">📅 Study Plan</h1>
        {selectedPlan ? (
          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold">{selectedPlan.subject}</h2>
              <p className="text-gray-600">
                Exam Date: {new Date(selectedPlan.exam_date).toLocaleDateString()} 
                {' • '}
                {selectedPlan.meta.total_sessions} sessions
              </p>
            </div>
            
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
          </div>
        ) : (
          <p className="text-gray-500">No study plan created yet. Go to Dashboard to create one!</p>
        )}
      </div>

      {selectedPlan && (
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
    </div>
  )
}
