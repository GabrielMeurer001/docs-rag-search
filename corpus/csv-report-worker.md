## Envio e acompanhamento {#envio-e-acompanhamento}

1. **Enviar.** Faça `POST /reports` com o CSV no campo `file` de um formulário `multipart/form-data`.
2. **Confirmar o envio.** Quando aceito, a API retorna `202 Accepted`, um `id` no JSON e a URL de consulta no cabeçalho `Location`.
3. **Acompanhar o processamento.** Abra a URL de `Location` ou faça `GET /reports/{id}`. Repita o GET enquanto o estado for `pending` ou `processing`. Em `completed`, o JSON traz o resultado. Em `failed`, consulte o campo `error`. Um UUID desconhecido retorna `404`.

```powershell
$job = curl.exe -sS -F "file=@examples/sales.csv" http://localhost:8080/reports | ConvertFrom-Json
curl.exe -i "http://localhost:8080/reports/$($job.id)"
```

Na interface web do CSV Report Worker local, abra http://localhost:8080, selecione o CSV e clique em **Gerar relatório**. A tela consulta o estado a cada segundo enquanto o trabalho estiver pendente ou em processamento. Use **Consultar por ID** para reabrir um trabalho existente.

## Formato do CSV {#formato-do-csv}

Use UTF-8, cabeçalho `sale_id,category,amount` e pelo menos uma venda. Cada venda ocupa uma linha física e inclui os três campos. O valor deve ser decimal não negativo, com ponto como separador e até duas casas. Um campo entre aspas pode conter vírgula.

```csv
sale_id,category,amount
1,livros,49.90
2,jogos,120.00
3,livros,30.10
```

Cada linha válida conta como uma venda. Nesse exemplo fictício, são três vendas e total de `200.00`. O resultado traz `saleCount`, `total` e `totalsByCategory`. Os valores monetários são strings com duas casas. Arquivos acima de 1 MiB recebem `413 FILE_TOO_LARGE`.

## Reentregas da fila {#reentregas}

A mensagem da fila contém o UUID do trabalho. Se o RabbitMQ entregar outra vez uma mensagem para um trabalho já em `completed` ou `failed`, o worker confirma a entrega e preserva o estado final. Uma nova entrega de um trabalho em `processing` pode retomar o processamento a partir do CSV no banco.

Na demo há um consumidor, com prefetch de uma mensagem. O worker confirma o consumo depois que a operação no banco termina. Uma reentrega do mesmo UUID e um novo envio do mesmo arquivo são operações distintas. Cada novo `POST /reports` cria outro UUID.

## Falhas de validação do CSV {#falhas-de-validacao}

Para identificar um trabalho que falhou, consulte `GET /reports/{id}` e procure `status: failed`. Leia `error.code` para identificar a causa. Se o arquivo tiver um valor inválido, o envio ainda pode ter sido aceito com `202`, pois o worker valida o conteúdo em segundo plano.

Um CSV inválido encerra o trabalho na primeira tentativa com `error.code: INVALID_CSV`, mensagem e número físico da linha em `error.line`. No exemplo fictício abaixo, `amount` na linha 3 tem valor `abc`.

```csv
sale_id,category,amount
1,livros,49.90
2,jogos,abc
```

## Falhas operacionais no worker {#falhas-operacionais}

Consulte `GET /reports/{id}`. Um trabalho em `status: failed` terminou com falha. Leia `error.code` para identificar a causa. Em caso de falha operacional, o worker faz até três tentativas, com pausas de um e dois segundos antes das novas tentativas.

Ao esgotar as tentativas, o worker tenta gravar `failed` com `error.code: PROCESSING_FAILED` e rejeita a mensagem. O RabbitMQ encaminha a rejeição para `reports.dlq`. Se a gravação falhar porque o banco continua indisponível, procure o UUID no log e na fila de mensagens rejeitadas. Depois que o banco voltar, a consulta pode mostrar o último estado que conseguiu gravar.

## Indisponibilidade do broker {#broker-indisponivel}

A API grava o trabalho como `pending` antes de publicar o UUID e espera até três segundos pela confirmação de publicação com roteamento. Se a publicação falhar, tenta registrar `failed` com `QUEUE_UNAVAILABLE` somente enquanto o trabalho estiver em `pending`.

Nesse cenário, o cliente pode receber `503` com ID e `Location` para consulta. Se o worker já tiver assumido o trabalho, a API preserva seu estado e retorna `202`. Uma queda entre o commit e a publicação pode deixar o trabalho em `pending` indefinidamente.
