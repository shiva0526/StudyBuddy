import { useState, useEffect } from 'react'

export default function QuizGame({ username, topic, onClose }) {
  const [quiz, setQuiz] = useState(null)
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answers, setAnswers] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    generateQuiz()
  }, [])

  const generateQuiz = async () => {
    try {
      const response = await fetch('/api/generate_quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          topic,
          num_questions: 5,
          difficulty: 'medium'
        })
      })
      const data = await response.json()
      setQuiz(data)
      setAnswers(new Array(data.questions.length).fill(-1))
      setLoading(false)
    } catch (error) {
      console.error('Error generating quiz:', error)
      setLoading(false)
    }
  }

  const handleAnswer = (choiceIndex) => {
    const newAnswers = [...answers]
    newAnswers[currentQuestion] = choiceIndex
    setAnswers(newAnswers)

    if (currentQuestion < quiz.questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1)
    }
  }

  const submitQuiz = async () => {
    try {
      const response = await fetch('/api/submit_quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          quiz_id: quiz.quiz_id,
          answers
        })
      })
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Error submitting quiz:', error)
    }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-8 text-center">
          <div className="animate-spin text-6xl mb-4">⚙️</div>
          <p>Generating quiz...</p>
        </div>
      </div>
    )
  }

  if (result) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-xl p-8 max-w-2xl w-full">
          <div className="text-center mb-6">
            <div className="text-6xl mb-4">
              {result.score >= 80 ? '🎉' : result.score >= 60 ? '👍' : '📚'}
            </div>
            <h2 className="text-3xl font-bold mb-2">{result.score}%</h2>
            <p className="text-gray-600">{result.correct} out of {result.total} correct</p>
          </div>

          <div className="mb-6">
            <div className="bg-primary h-4 rounded-full overflow-hidden">
              <div 
                className="bg-accent h-full transition-all"
                style={{ width: `${result.score}%` }}
              />
            </div>
          </div>

          <div className="space-y-4 mb-6">
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="font-semibold text-green-800">+{result.xp_earned} XP Earned!</p>
            </div>

            {result.feedback.map((fb, idx) => (
              <div key={idx} className="p-4 bg-blue-50 rounded-lg">
                <p className="text-blue-800">{fb}</p>
              </div>
            ))}
          </div>

          <div className="flex space-x-3">
            <button onClick={onClose} className="btn-primary flex-1">
              Continue Learning
            </button>
            <button onClick={generateQuiz} className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-2 px-6 rounded-lg">
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const question = quiz.questions[currentQuestion]

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-8 max-w-2xl w-full">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">Quiz: {topic}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl">×</button>
        </div>

        <div className="mb-6">
          <p className="text-sm text-gray-500 mb-2">
            Question {currentQuestion + 1} of {quiz.questions.length}
          </p>
          <div className="bg-gray-200 h-2 rounded-full">
            <div 
              className="bg-primary h-2 rounded-full transition-all"
              style={{ width: `${((currentQuestion + 1) / quiz.questions.length) * 100}%` }}
            />
          </div>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-4">{question.stem}</h3>
          <div className="space-y-3">
            {question.choices.map((choice, idx) => (
              <button
                key={idx}
                onClick={() => handleAnswer(idx)}
                className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                  answers[currentQuestion] === idx
                    ? 'border-primary bg-primary bg-opacity-10'
                    : 'border-gray-200 hover:border-primary'
                }`}
              >
                <span className="font-semibold mr-2">{String.fromCharCode(65 + idx)}.</span>
                {choice}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-between">
          <button
            onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
            disabled={currentQuestion === 0}
            className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-2 px-6 rounded-lg disabled:opacity-50"
          >
            ← Back
          </button>
          
          {currentQuestion === quiz.questions.length - 1 ? (
            <button
              onClick={submitQuiz}
              className="btn-primary"
            >
              Submit Quiz
            </button>
          ) : (
            <button
              onClick={() => setCurrentQuestion(currentQuestion + 1)}
              className="btn-primary"
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
