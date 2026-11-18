# docs-rag-search

Faça perguntas sobre o CSV Report Worker e abra os trechos do guia que sustentam cada resposta. A demo usa FastAPI, PostgreSQL com pgvector, Ollama local e uma interface React.

## Rodar no Windows

Use Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24, Docker Desktop com Compose e [Ollama para Windows](https://docs.ollama.com/windows). Com Docker e Ollama ativos, execute os comandos abaixo na raiz.

```powershell
docker compose up -d --wait db
ollama pull bge-m3:latest
ollama pull qwen3.5:4b
uv sync --locked
uv run --locked python -m docs_rag index
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
uv run --locked python -m uvicorn docs_rag.app:app --host 127.0.0.1 --port 8000
```

Abra [a busca](http://127.0.0.1:8000). Experimente a pergunta de envio de CSV e siga `[1]` até **Abrir seção original**. A pergunta sobre SSO demonstra a falta de evidência. A primeira chamada aos modelos pode demorar mais enquanto são carregados.

O banco escuta em `127.0.0.1:25433` e o Ollama em `127.0.0.1:11434`. Para desenvolver a interface com recarga automática, mantenha a API ativa e rode `npm.cmd --prefix frontend run dev`. Para encerrar a demo, interrompa o Uvicorn e execute `docker compose down`, que preserva o volume do banco.

## Corpus e API

O [manifesto](corpus/manifest.json) referencia um guia de operação reescrito a partir da revisão `0d3f375` do CSV Report Worker. Os dados dos exemplos são fictícios. Revise o guia e confirme a permissão de publicação antes de abrir uma vitrine pública.

Depois de editar o guia, execute `uv run --locked python -m docs_rag index`. Cada título precisa de uma âncora no formato `{#secao}`. A reindexação reaproveita embeddings quando o conteúdo e o modelo coincidem, remove trechos antigos e publica o guia inteiro numa transação. Se a versão do modelo de embeddings mudar, execute o comando novamente para regenerar o índice.

A busca usa os três vizinhos exatos por cosseno. O Ollama responde com referências aos trechos recuperados. O servidor valida essas referências antes de montar as citações e os links para o guia. As perguntas e os trechos são processados localmente.

`POST /api/ask` recebe `{"question":"Como envio um CSV e acompanho o processamento?"}`. Os estados estão documentados no [OpenAPI local](http://127.0.0.1:8000/docs).

| HTTP | Estado | Corpo |
| --- | --- | --- |
| 200 | `answered` | `blocks` com texto e números das citações, e `sources` com trechos e URLs. |
| 200 | `insufficient_evidence` | Mensagem de insuficiência de evidência. |
| 503 | `temporarily_unavailable` | Mensagem e `retryable: true`. |
| 422 | Entrada inválida | Erro de validação. Aceita de 1 a 500 caracteres depois de aparar espaços. |

Estas variáveis de ambiente controlam a configuração local.

| Variável | Padrão |
| --- | --- |
| `DOCS_RAG_DATABASE_URL` | `postgresql://docs_rag:docs-rag-local@127.0.0.1:25433/docs_rag` |
| `DOCS_RAG_OLLAMA_URL` | `http://127.0.0.1:11434` |
| `DOCS_RAG_EMBEDDING_MODEL` | `bge-m3:latest`, 1.024 dimensões |
| `DOCS_RAG_ANSWER_MODEL` | `qwen3.5:4b`, saída estruturada |

## Testes e avaliação

Com o banco do Compose ativo, rode os testes de Python.

```powershell
$env:DOCS_RAG_TEST_DATABASE_URL = 'postgresql://docs_rag:docs-rag-local@127.0.0.1:25433/docs_rag'
uv run --locked python -m pytest
```

O teste de integração cria e remove um esquema isolado. Os testes da API usam um cliente de modelo falso. Com API, índice e Ollama ativos, rode o Playwright no desktop e em viewport de 320 px.

```powershell
cd frontend
npx.cmd playwright install chromium
npm.cmd run test:e2e
cd ..
```

O Playwright valida resposta e citação com modelos reais, insuficiência para SSO e uma resposta `503` simulada no navegador seguida de nova tentativa real.

```powershell
uv run --locked python -m docs_rag evaluate --output evaluation-local.json
```

As [perguntas versionadas](evaluation/questions.json) definem as seções e os fatos esperados. O avaliador registra ranks, `Hit@1`, `Hit@3`, tempos, digests, blocos e fontes. Use os fatos esperados e os trechos citados para revisar cada afirmação. Os [resultados locais registrados](evaluation/results.md) incluem a revisão manual de cada resposta.
