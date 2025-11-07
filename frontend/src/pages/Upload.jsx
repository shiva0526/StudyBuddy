import { useState, useEffect } from 'react'

export default function Upload({ username }) {
  const [resources, setResources] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')

  useEffect(() => {
    fetchResources()
  }, [username])

  const fetchResources = async () => {
    try {
      const response = await fetch(`/api/resources/${username}`)
      const data = await response.json()
      setResources(data.resources || [])
    } catch (error) {
      console.error('Error fetching resources:', error)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    formData.append('username', username)
    formData.append('type', file.name.endsWith('.pdf') ? 'notes' : 'notes')

    setUploading(true)
    setUploadProgress('Uploading...')

    try {
      const response = await fetch('/api/upload_resource', {
        method: 'POST',
        body: formData
      })

      const data = await response.json()
      setUploadProgress(`✓ Indexed ${data.chunks_indexed} chunks`)
      
      setTimeout(() => {
        setUploadProgress('')
        setUploading(false)
        fetchResources()
      }, 2000)
    } catch (error) {
      console.error('Upload error:', error)
      setUploadProgress('❌ Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h1 className="text-2xl font-bold mb-4">Upload Study Materials</h1>
        <p className="text-gray-600 mb-6">Upload your notes, past papers, and study materials. We'll index them for AI-powered learning.</p>
        
        <div className="border-2 border-dashed border-primary rounded-lg p-8 text-center">
          <div className="mb-4">
            <div className="text-6xl mb-4">📤</div>
            <p className="text-lg font-semibold mb-2">Drop files here or click to browse</p>
            <p className="text-sm text-gray-500">Supports PDF and text files</p>
          </div>
          
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileUpload}
            disabled={uploading}
            className="hidden"
            id="file-upload"
          />
          
          <label
            htmlFor="file-upload"
            className={`btn-primary inline-block cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {uploading ? 'Processing...' : 'Choose File'}
          </label>
          
          {uploadProgress && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg text-blue-800">
              {uploadProgress}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-4">Your Resources ({resources.length})</h2>
        
        {resources.length === 0 ? (
          <p className="text-gray-500">No resources uploaded yet. Start by uploading your study materials!</p>
        ) : (
          <div className="space-y-3">
            {resources.map((resource) => (
              <div key={resource.resource_id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div className="flex items-center space-x-3">
                  <div className="text-3xl">
                    {resource.filename.endsWith('.pdf') ? '📄' : '📝'}
                  </div>
                  <div>
                    <p className="font-semibold">{resource.filename}</p>
                    <p className="text-sm text-gray-500">
                      {resource.chunks} chunks • Uploaded {new Date(resource.uploaded_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {resource.indexed && (
                    <span className="bg-green-100 text-green-800 text-xs font-semibold px-3 py-1 rounded-full">
                      ✓ Indexed
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
