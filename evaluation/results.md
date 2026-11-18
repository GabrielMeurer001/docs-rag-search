# Avaliação local · 17/11/2026

Corpus de seis trechos do guia baseado no CSV Report Worker na revisão `0d3f375`. A indexação repetida manteve os seis trechos e gerou zero embeddings novos.

## Recuperação e resposta

**Hit@1 de 3/4 e Hit@3 de 4/4.** O ranking mede a primeira seção esperada em cada pergunta coberta. Os dois casos fora do corpus retornaram `insufficient_evidence` com os modelos reais.

| Caso | Posição da seção esperada | Recuperação | Geração | Revisão das citações |
| --- | ---: | ---: | ---: | --- |
| Envio | 1 | 129 ms | 2.168 ms | A seção de envio sustenta o POST multipart, o `202`, o ID, o `Location` e a consulta até o estado final. |
| Reentrega | 1 | 95 ms | 1.295 ms | A seção de reentregas sustenta a preservação de `completed` e `failed` e a possibilidade de retomar `processing`. |
| Falha | 1 | 73 ms | 1.316 ms | As seções de falhas operacionais e de validação sustentam a consulta por ID, `failed` e `error.code`. |
| Consulta por ID | 2 | 97 ms | 1.676 ms | A seção de envio sustenta `GET /reports/{id}`, a espera por `pending` e `processing` e o resultado em `completed`. |
| SSO | — | 78 ms | 590 ms | Insuficiência de evidência. |
| Exportação agendada | — | 89 ms | 443 ms | Insuficiência de evidência. |

Os tempos são de uma execução no Windows com GPU RTX 3060 Ti e modelos já carregados. O avaliador mede recuperação e geração separadamente e registra os trechos usados. Os fatos e o suporte das citações da tabela foram conferidos manualmente.

## Ambiente e interface

- Python 3.13.14, PostgreSQL 16.14 com pgvector 0.8.2, Ollama 0.33.2 e Node.js 24.16.0. As dependências da aplicação estão nos arquivos de lock.
- `bge-m3:latest`, digest `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`.
- `qwen3.5:4b`, digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`.
- Os seis cenários Playwright passaram no Chromium. Em desktop e a 320 px, foram verificados resposta real com citação e âncora, insuficiência para SSO e nova tentativa real após um `503` simulado. A ativação da citação por teclado transferiu o foco para a fonte e o botão de retorno devolveu o foco à citação.
