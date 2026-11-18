import { StrictMode, useEffect, useRef, useState } from 'react'
import type { FormEvent, MouseEvent } from 'react'
import { createRoot } from 'react-dom/client'
import { ask, unavailable } from './api'
import type { Answered, Source } from './api'
import './styles.css'

const examples = [
  'Como envio um CSV e acompanho o processamento?',
  'O que acontece se uma mensagem for entregue duas vezes?',
  'Como configuro autenticação por SSO?',
]

type Selection = { source: number; trigger: HTMLAnchorElement }
type View = Awaited<ReturnType<typeof ask>> | { status: 'loading' }

function SourceCard({ source, selection }: { source: Source; selection: Selection | null }) {
  return (
    <article
      className="source-card" id={`fonte-${source.number}`} tabIndex={-1}
      data-selected={selection?.source === source.number}
      aria-labelledby={`titulo-fonte-${source.number}`}
    >
      <header className="source-heading">
        <span className="source-number">[{source.number}]</span>
        <div>
          <h3 id={`titulo-fonte-${source.number}`}>{source.section_title}</h3>
          <p>{source.document_title}</p>
        </div>
      </header>
      <pre className="excerpt">{source.excerpt}</pre>
      <div className="source-actions">
        <a href={source.url}>Abrir seção original <span aria-hidden="true">↗</span></a>
        {selection?.source === source.number && (
          <button type="button" className="return-link" onClick={() => selection.trigger.focus()}>
            Voltar à citação
          </button>
        )}
      </div>
    </article>
  )
}

function SearchResult({ result }: { result: Answered }) {
  const [selection, setSelection] = useState<Selection | null>(null)
  const [sourcesOpen, setSourcesOpen] = useState(false)

  useEffect(() => {
    if (!selection) return
    const source = document.getElementById(`fonte-${selection.source}`)
    source?.focus({ preventScroll: true })
    source?.scrollIntoView({ block: 'nearest' })
  }, [selection])

  function selectSource(event: MouseEvent<HTMLAnchorElement>, source: number) {
    if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return
    event.preventDefault()
    setSourcesOpen(true)
    setSelection({ source, trigger: event.currentTarget })
  }

  return (
    <div className="result-grid">
      <section className="answer" aria-labelledby="answer-title">
        <h2 id="answer-title">Resposta</h2>
        {result.blocks.map((block, index) => (
          <p className="answer-block" key={index}>
            {block.text}{' '}
            <span className="citations">
              {block.citations.map((number) => (
                <a key={number} href={`#fonte-${number}`} className="citation"
                  aria-label={`Fonte ${number}`}
                  onClick={(event) => selectSource(event, number)}>[{number}]</a>
              ))}
            </span>
          </p>
        ))}
      </section>
      <aside className="sources" aria-label="Fontes">
        <h2 className="sources-heading">Fontes <span>{result.sources.length}</span></h2>
        <button type="button" className="sources-toggle"
          aria-expanded={sourcesOpen} aria-controls="source-list"
          onClick={() => setSourcesOpen(!sourcesOpen)}>
          Fontes ({result.sources.length}) <span aria-hidden="true">{sourcesOpen ? '−' : '+'}</span>
        </button>
        <div className="source-list" id="source-list" data-open={sourcesOpen}>
          {result.sources.map((source) => (
            <SourceCard key={source.chunk_id} source={source} selection={selection} />
          ))}
        </div>
      </aside>
    </div>
  )
}

function App() {
  const [question, setQuestion] = useState('')
  const [view, setView] = useState<View | null>(null)
  const running = useRef(false)
  const input = useRef<HTMLInputElement>(null)
  const submitted = useRef('')
  const loading = view?.status === 'loading'

  async function submit(value: string) {
    if (running.current) return
    const clean = value.trim()
    if (!clean || [...clean].length > 500) {
      setView({ status: 'invalid_question', message: 'Digite uma pergunta de até 500 caracteres.' })
      input.current?.focus()
      return
    }
    running.current = true
    submitted.current = clean
    setQuestion(clean)
    input.current?.focus()
    setView({ status: 'loading' })
    try {
      setView(await ask(clean))
    } catch {
      setView(unavailable)
    } finally {
      running.current = false
    }
  }

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submit(question)
  }

  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <a className="wordmark" href="/"><span className="brand-mark" aria-hidden="true" /> docs-rag-search</a>
          <a className="guide-link" href="/guia/csv-report-worker">Guia de operação <span aria-hidden="true">↗</span></a>
        </div>
      </header>
      <main className="page">
        <section className="search-section" aria-labelledby="page-title">
          <p className="corpus-name">CSV Report Worker</p>
          <h1 id="page-title">Busca na documentação</h1>
          <p className="intro">Faça uma pergunta sobre o worker e confira os trechos do guia usados na resposta.</p>
          <form className="search-form" onSubmit={search}>
            <label className="sr-only" htmlFor="question">Sua pergunta</label>
            <div className="input-wrap">
              <span className="search-icon" aria-hidden="true" />
              <input id="question" ref={input} value={question} onChange={(event) => setQuestion(event.target.value)}
                placeholder="Digite sua pergunta" autoComplete="off"
                readOnly={loading} aria-invalid={view?.status === 'invalid_question' || undefined} />
            </div>
            <button className="primary" type="submit" disabled={loading}>Buscar</button>
          </form>
          <div className="example-area">
            <p>Experimente uma pergunta</p>
            <ul className="examples">
              {examples.map((example) => (
                <li key={example}>
                  <button type="button" disabled={loading} onClick={() => void submit(example)}>
                    {example} <span aria-hidden="true">↗</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
        <div className="sr-only" role="status" aria-atomic="true">
          {view?.status === 'answered' && 'Resposta disponível.'}
          {view?.status === 'loading' && 'Consultando a documentação…'}
          {view && 'message' in view && view.message}
        </div>
        {view?.status === 'answered' && <SearchResult result={view} />}
        {view && view.status !== 'answered' && (
          <section className="notice" data-state={view.status} aria-label="Resultado da busca">
            {view.status === 'loading'
              ? <p><span className="loading-mark" aria-hidden="true" /> Consultando a documentação…</p>
              : <p>{view.message}</p>}
            {view.status === 'temporarily_unavailable' && (
              <button className="secondary" type="button" onClick={() => void submit(submitted.current)}>
                Tentar novamente
              </button>
            )}
          </section>
        )}
      </main>
    </>
  )
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
