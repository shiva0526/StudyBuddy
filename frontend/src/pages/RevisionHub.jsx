import { useState } from 'react'
import Flashcards from '../components/Flashcards'

export default function RevisionHub({ username }) {
  const [revisionPack, setRevisionPack] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showFlashcards, setShowFlashcards] = useState(false)

  const generateRevisionPack = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/generate_revision_pack', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          options: { max_flashcards: 20, concise: true }
        })
      })
      const data = await response.json()
      setRevisionPack(data)
      setLoading(false)
    } catch (error) {
      console.error('Error generating revision pack:', error)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h1 className="text-2xl font-bold mb-4">📚 Revision Hub</h1>
        <p className="text-gray-600 mb-6">
          Generate AI-powered revision materials tailored to your weak topics and study history.
        </p>
        
        <button onClick={generateRevisionPack} disabled={loading} className="btn-primary">
          {loading ? '⚙️ Generating...' : '✨ Generate Revision Pack'}
        </button>
      </div>

      {revisionPack && (
        <>
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">📝 Short Notes</h2>
              {revisionPack.download_url && (
                <a
                  href={revisionPack.download_url}
                  download
                  className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm"
                >
                  ⬇️ Download
                </a>
              )}
            </div>
            
            {revisionPack.short_notes?.length > 0 ? (
              <ul className="space-y-2">
                {revisionPack.short_notes.map((note, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <span className="text-gray-700">{note}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No notes generated</p>
            )}
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">🃏 Flashcards ({revisionPack.flashcards?.length || 0})</h2>
              <button
                onClick={() => setShowFlashcards(!showFlashcards)}
                className="btn-secondary text-sm"
              >
                {showFlashcards ? 'Hide' : 'Play'} Flashcards
              </button>
            </div>
            
            {showFlashcards && revisionPack.flashcards?.length > 0 && (
              <Flashcards cards={revisionPack.flashcards} username={username} />
            )}
            
            {!showFlashcards && revisionPack.flashcards?.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {revisionPack.flashcards.slice(0, 6).map((card, idx) => (
                  <div key={idx} className="p-4 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg">
                    <p className="font-semibold text-sm mb-2">{card.front}</p>
                    <p className="text-xs text-gray-600">{card.back}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {revisionPack.mnemonics?.length > 0 && (
            <div className="card">
              <h2 className="text-xl font-bold mb-4">🧠 Memory Aids</h2>
              <div className="space-y-3">
                {revisionPack.mnemonics.map((mnemonic, idx) => (
                  <div key={idx} className="p-3 bg-yellow-50 rounded-lg border-l-4 border-yellow-400">
                    <p className="text-gray-700">{mnemonic}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
