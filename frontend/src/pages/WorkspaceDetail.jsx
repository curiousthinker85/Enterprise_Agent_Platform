import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'

export default function WorkspaceDetail() {
  const { id } = useParams()
  const [workspace, setWorkspace] = useState(null)
  const [documents, setDocuments] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [docBusy, setDocBusy] = useState(null)
  const fileRef = useRef(null)

  // search
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)

  // ask
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)

  // member form
  const [memberForm, setMemberForm] = useState({ email: '', role: 'MEMBER' })

  const load = () => {
    api.getWorkspace(id).then(setWorkspace).catch((e) => setError(e.message))
    api.listDocuments(id).then(setDocuments).catch((e) => setError(e.message))
    api.listMembers(id).then(setMembers).catch(() => {})
  }

  useEffect(load, [id])

  const flash = (msg) => {
    setNotice(msg)
    setTimeout(() => setNotice(''), 4000)
  }

  const upload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setDocBusy('upload')
    setError('')
    try {
      await api.uploadDocument(id, file)
      flash(`Uploaded "${file.name}"`)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setDocBusy(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const runStep = async (docId, step, fn, msg) => {
    setDocBusy(`${step}-${docId}`)
    setError('')
    try {
      await fn()
      flash(msg)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setDocBusy(null)
    }
  }

  const doSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError('')
    try {
      const res = await api.searchWorkspace(id, query.trim())
      setResults(res.results)
    } catch (err) {
      setError(err.message)
    } finally {
      setSearching(false)
    }
  }

  const doAsk = async (e) => {
    e.preventDefault()
    if (!question.trim()) return
    setAsking(true)
    setError('')
    try {
      const res = await api.askWorkspace(id, { question: question.trim(), top_k: 5 })
      setAnswer(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setAsking(false)
    }
  }

  const addMember = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.addMember(id, memberForm)
      flash('Member saved')
      setMemberForm({ email: '', role: 'MEMBER' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  if (!workspace) return <p className="muted">Loading…</p>

  return (
    <div>
      <div className="topbar">
        <div>
          <Link to="/">← All workspaces</Link>
          <h1 style={{ marginTop: 6 }}>{workspace.name} <span className="badge">{workspace.workspace_type}</span></h1>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="card">
        <h2>Ask the workspace (RAG)</h2>
        <form onSubmit={doAsk} className="flex">
          <input className="grow" placeholder="Ask a question about your documents…" value={question} onChange={(e) => setQuestion(e.target.value)} />
          <button disabled={asking}>{asking ? 'Thinking…' : 'Ask'}</button>
        </form>
        {answer && (
          <div style={{ marginTop: 14 }}>
            <div className="msg assistant" style={{ background: 'var(--panel-2)', padding: 14, borderRadius: 12, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
              {answer.answer}
            </div>
            {answer.model && <div className="muted" style={{ marginTop: 6 }}>Model: {answer.model}</div>}
            {answer.citations?.length > 0 && (
              <>
                <h3 style={{ margin: '12px 0 6px', fontSize: 14 }}>Sources</h3>
                {answer.citations.map((c) => (
                  <div key={c.citation_index} className="citation">
                    [{c.citation_index}] <strong>{c.document_filename}</strong> (chunk {c.chunk_index}, score {c.score?.toFixed(3)})
                    <div className="muted" style={{ marginTop: 4 }}>{c.content.slice(0, 220)}{c.content.length > 220 ? '…' : ''}</div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h2>Semantic search</h2>
        <form onSubmit={doSearch} className="flex">
          <input className="grow" placeholder="Search indexed chunks…" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button disabled={searching}>{searching ? 'Searching…' : 'Search'}</button>
        </form>
        {results !== null && (
          <div style={{ marginTop: 14 }}>
            {results.length === 0 && <p className="muted">No results. Upload, process and index documents first.</p>}
            {results.map((r, i) => (
              <div key={i} className="search-result">
                <strong>{r.document_filename}</strong> <span className="muted">chunk {r.chunk_index} · score {r.score?.toFixed(3)}</span>
                <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{r.content.slice(0, 300)}{r.content.length > 300 ? '…' : ''}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="flex" style={{ justifyContent: 'space-between' }}>
          <h2>Documents</h2>
          <label className="secondary small" style={{ margin: 0 }}>
            <button type="button" onClick={() => fileRef.current?.click()} disabled={docBusy === 'upload'}>
              {docBusy === 'upload' ? 'Uploading…' : 'Upload file'}
            </button>
            <input ref={fileRef} type="file" hidden onChange={upload} />
          </label>
        </div>
        {documents.length === 0 ? (
          <p className="muted">No documents yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Name</th><th>Size</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                <tr key={d.id}>
                  <td>{d.original_filename}</td>
                  <td>{(d.size_bytes / 1024).toFixed(1)} KB</td>
                  <td><span className={`badge ${d.status}`}>{d.status}</span></td>
                  <td className="flex">
                    {d.status === 'new' && (
                      <button className="small secondary" disabled={docBusy === `process-${d.id}`}
                        onClick={() => runStep(d.id, 'process', () => api.processDocument(d.id), `Processed "${d.original_filename}"`)}>
                        Process
                      </button>
                    )}
                    {d.status === 'processed' && (
                      <button className="small" disabled={docBusy === `index-${d.id}`}
                        onClick={() => runStep(d.id, 'index', () => api.indexDocument(d.id), `Indexed "${d.original_filename}"`)}>
                        Index
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Members</h2>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th></tr></thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}><td>{m.full_name}</td><td>{m.email}</td><td><span className="badge">{m.role}</span></td></tr>
            ))}
          </tbody>
        </table>
        <form onSubmit={addMember} className="flex" style={{ marginTop: 14, alignItems: 'flex-end' }}>
          <div className="grow">
            <label>Add member by email (must be registered)</label>
            <input type="email" value={memberForm.email} onChange={(e) => setMemberForm({ ...memberForm, email: e.target.value })} required />
          </div>
          <div>
            <label>Role</label>
            <select value={memberForm.role} onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}>
              <option>ADMIN</option><option>MEMBER</option><option>VIEWER</option>
            </select>
          </div>
          <button>Save</button>
        </form>
      </div>
    </div>
  )
}
