'use client'

import { useEffect, useState } from 'react'

export default function TestGitHubConfig() {
  const [clientId, setClientId] = useState<string | null>(null)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL
  const apiUrl = process.env.NEXT_PUBLIC_API_URL

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch('/api/github/config')
        if (!response.ok) {
          return
        }

        const data = await response.json()
        setClientId(data.clientId || null)
      } catch (error) {
        console.error('[GitHub Config] Failed to load config:', error)
      }
    }

    void loadConfig()
  }, [])

  const testRedirect = () => {
    const redirectUri = encodeURIComponent(`${window.location.origin}/api/github/callback`)
    const scope = 'repo,read:user'
    const state = crypto.randomUUID()

    document.cookie = `github_oauth_state=${state}; path=/; max-age=600; samesite=lax`
    
    const url = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}&state=${state}`
    
    alert(`Will redirect to: ${url}`)
    
    window.location.href = url
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">GitHub OAuth Configuration Test</h1>
      
      <div className="space-y-4 mb-8">
        <div className="border p-4 rounded">
          <h2 className="font-semibold">Environment Variables:</h2>
          <ul className="mt-2 space-y-2">
            <li>
              <strong>NEXT_PUBLIC_GITHUB_CLIENT_ID:</strong>{' '}
              <code className="bg-gray-100 px-2 py-1 rounded">
                {clientId || '❌ NOT SET'}
              </code>
            </li>
            <li>
              <strong>NEXT_PUBLIC_BACKEND_URL:</strong>{' '}
              <code className="bg-gray-100 px-2 py-1 rounded">
                {backendUrl || '❌ NOT SET'}
              </code>
            </li>
            <li>
              <strong>NEXT_PUBLIC_API_URL:</strong>{' '}
              <code className="bg-gray-100 px-2 py-1 rounded">
                {apiUrl || '❌ NOT SET'}
              </code>
            </li>
          </ul>
        </div>

        <div className="border p-4 rounded">
          <h2 className="font-semibold">Computed Values:</h2>
          <ul className="mt-2 space-y-2">
            <li>
              <strong>Window Origin:</strong>{' '}
              <code className="bg-gray-100 px-2 py-1 rounded">
                {typeof window !== 'undefined' ? window.location.origin : 'N/A'}
              </code>
            </li>
            <li>
              <strong>Callback URL:</strong>{' '}
              <code className="bg-gray-100 px-2 py-1 rounded">
                {typeof window !== 'undefined' 
                  ? `${window.location.origin}/api/github/callback`
                  : 'N/A'}
              </code>
            </li>
          </ul>
        </div>
      </div>

      <button
        onClick={testRedirect}
        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        disabled={!clientId}
      >
        Test GitHub OAuth Redirect
      </button>

      {!clientId && (
        <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          <strong>Error:</strong> NEXT_PUBLIC_GITHUB_CLIENT_ID is not set!
          <br />
          <br />
          Please check:
          <ul className="list-disc ml-6 mt-2">
            <li>frontend/.env.local file exists</li>
            <li>Contains: NEXT_PUBLIC_GITHUB_CLIENT_ID=your_github_client_id</li>
            <li>Frontend server was restarted after adding the variable</li>
          </ul>
        </div>
      )}
    </div>
  )
}
