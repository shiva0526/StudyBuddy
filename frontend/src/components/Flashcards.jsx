import { useState } from 'react'

export default function Flashcards({ cards, username }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)

  const handleNext = () => {
    setFlipped(false)
    setCurrentIndex((prev) => (prev + 1) % cards.length)
  }

  const handlePrev = () => {
    setFlipped(false)
    setCurrentIndex((prev) => (prev - 1 + cards.length) % cards.length)
  }

  if (!cards || cards.length === 0) {
    return <p className="text-gray-500">No flashcards available</p>
  }

  const card = cards[currentIndex]

  return (
    <div className="space-y-4">
      <div className="text-center">
        <p className="text-sm text-gray-500 mb-2">
          Card {currentIndex + 1} of {cards.length}
        </p>
        <div className="bg-gray-200 h-2 rounded-full max-w-xs mx-auto">
          <div 
            className="bg-primary h-2 rounded-full transition-all"
            style={{ width: `${((currentIndex + 1) / cards.length) * 100}%` }}
          />
        </div>
      </div>

      <div 
        className="relative h-64 cursor-pointer perspective-1000"
        onClick={() => setFlipped(!flipped)}
      >
        <div className={`absolute inset-0 transition-transform duration-500 transform-style-3d ${
          flipped ? 'rotate-y-180' : ''
        }`}>
          <div className="absolute inset-0 backface-hidden">
            <div className="h-full bg-gradient-to-br from-purple-400 to-blue-500 rounded-xl p-8 flex items-center justify-center text-white shadow-xl">
              <div className="text-center">
                <p className="text-sm mb-2 opacity-75">Question</p>
                <p className="text-2xl font-bold">{card.front}</p>
              </div>
            </div>
          </div>
          
          <div className="absolute inset-0 backface-hidden rotate-y-180">
            <div className="h-full bg-gradient-to-br from-green-400 to-teal-500 rounded-xl p-8 flex items-center justify-center text-white shadow-xl">
              <div className="text-center">
                <p className="text-sm mb-2 opacity-75">Answer</p>
                <p className="text-xl">{card.back}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <p className="text-center text-sm text-gray-500">Click card to flip</p>

      <div className="flex justify-between items-center">
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-2 px-6 rounded-lg disabled:opacity-50"
        >
          ← Previous
        </button>
        
        <div className="flex space-x-2">
          {cards.slice(0, 5).map((_, idx) => (
            <div 
              key={idx}
              className={`w-2 h-2 rounded-full ${
                idx === currentIndex ? 'bg-primary' : 'bg-gray-300'
              }`}
            />
          ))}
        </div>

        <button
          onClick={handleNext}
          className="bg-primary hover:bg-purple-700 text-white font-semibold py-2 px-6 rounded-lg"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
