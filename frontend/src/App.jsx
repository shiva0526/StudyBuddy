import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Plan from './pages/Plan'
import Session from './pages/Session'
import RevisionHub from './pages/RevisionHub'

function App() {
  const [username, setUsername] = useState(localStorage.getItem('username') || 'demo_user')
  const [user, setUser] = useState(null)

  useEffect(() => {
    fetchUser()
  }, [username])

  const fetchUser = async () => {
    try {
      const response = await fetch(`/api/user/${username}`)
      const data = await response.json()
      setUser(data)
    } catch (error) {
      console.error('Error fetching user:', error)
    }
  }

  const handleUsernameChange = (newUsername) => {
    setUsername(newUsername)
    localStorage.setItem('username', newUsername)
  }

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-cyan-50">
        <nav className="bg-white shadow-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-8">
                <Link to="/" className="text-2xl font-bold text-primary">
                  📚 StudyBuddy
                </Link>
                <div className="hidden md:flex space-x-4">
                  <Link to="/" className="text-gray-700 hover:text-primary px-3 py-2 rounded-md text-sm font-medium">
                    Dashboard
                  </Link>
                  <Link to="/upload" className="text-gray-700 hover:text-primary px-3 py-2 rounded-md text-sm font-medium">
                    Upload
                  </Link>
                  <Link to="/plan" className="text-gray-700 hover:text-primary px-3 py-2 rounded-md text-sm font-medium">
                    Study Plan
                  </Link>
                  <Link to="/revision" className="text-gray-700 hover:text-primary px-3 py-2 rounded-md text-sm font-medium">
                    Revision Hub
                  </Link>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                {user && (
                  <div className="flex items-center space-x-2">
                    <div className="text-right">
                      <p className="text-sm font-semibold text-gray-700">{user.name}</p>
                      <p className="text-xs text-gray-500">Level {user.level} • {user.xp} XP</p>
                    </div>
                    <div className="bg-primary text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
                      {user.name[0].toUpperCase()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard username={username} user={user} />} />
            <Route path="/upload" element={<Upload username={username} />} />
            <Route path="/plan" element={<Plan username={username} />} />
            <Route path="/session/:sessionId" element={<Session username={username} />} />
            <Route path="/revision" element={<RevisionHub username={username} />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
