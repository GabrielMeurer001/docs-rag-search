# Busca em documentação técnica com RAG

Projeto de portfólio para fazer perguntas sobre um conjunto pequeno de documentação pública e verificar quais trechos sustentam a resposta.

## Escopo inicial

- API em Python com FastAPI e busca em PostgreSQL com pgvector.
- Indexar documentação com licença compatível e manter os links para as seções de origem.
- Retornar a resposta e as fontes recuperadas, ou indicar que o material disponível é insuficiente.

## Critérios da primeira demo

1. Uma pergunta coberta pelo corpus retorna uma resposta que cita a seção esperada.
2. Uma pergunta fora do corpus retorna indicação de evidência insuficiente.
3. Um conjunto versionado de perguntas e fontes esperadas permite avaliar a recuperação separadamente da resposta gerada.

Estado atual: documentação inicial.
