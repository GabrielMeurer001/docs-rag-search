export type Source = {
  number: number
  chunk_id: string
  document_title: string
  section_title: string
  excerpt: string
  url: string
}

export type Answered = {
  status: 'answered'
  blocks: { text: string; citations: number[] }[]
  sources: Source[]
}

type Unavailable = {
  status: 'temporarily_unavailable'
  message: string
  retryable: true
}

type Result = Answered | Unavailable | {
  status: 'insufficient_evidence' | 'invalid_question'
  message: string
}

export const unavailable: Unavailable = {
  status: 'temporarily_unavailable',
  message: 'A busca está temporariamente indisponível.',
  retryable: true,
}

export async function ask(question: string): Promise<Result> {
  const response = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal: AbortSignal.timeout(90_000),
  })
  if (response.status === 422) {
    return { status: 'invalid_question', message: 'Digite uma pergunta de até 500 caracteres.' }
  }
  if (!response.ok) return unavailable
  const result = await response.json()
  if (result.status === 'answered' || result.status === 'insufficient_evidence') return result
  return unavailable
}
