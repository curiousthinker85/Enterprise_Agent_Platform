import { useState } from 'react'
import { api } from '../api/client'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [modelTest, setModelTest] = useState(null)

  const send = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setBusy(true)
    setError('')
    try {
      const res = await api.chat({ messages: next })
      setMessages([...next, { role: 'assistant', content: res.content }])
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const testModel = async () => {
    setModelTest(null)
    setError('')
    try {
      const res = await api.testModel()
      setModelTest(`✓ ${res.model}: ${res.message}`)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="topbar">
        <h1 style={{ margin: 0 }}>AI Chat</h1>
        <button className="secondary small" onClick={testModel}>Test model connection</button>
      </div>
      {modelTest && <div className="success">{modelTest}</div>}
      {error && <div className="error">{error}</div>}

      <div className="card" style={{ minHeight: 340 }}>
        {messages.length === 0 ? (
          <p className="muted">Send a message to talk directly to the configured LLM (no document context — use a workspace for RAG).</p>
        ) : (
          <div className="chat">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>{m.content}</div>
            ))}
            {busy && <div className="msg assistant">Thinking…</div>}
          </div>
        )}
      </div>

      <form onSubmit={send} className="flex">
        <input className="grow" placeholder="Type a message…" value={input} onChange={(e) => setInput(e.target.value)} />
        <button disabled={busy}>Send</button>
      </form>
    </div>
  )
}
