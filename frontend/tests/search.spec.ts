import { expect, test } from '@playwright/test'

const UPLOAD = 'Como envio um CSV e acompanho o processamento?'
const SECTION = '/guia/csv-report-worker#envio-e-acompanhamento'
const SSO = 'Como configuro autenticação por SSO?'

test('responde sobre envio e abre a seção que sustenta a resposta', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Busca na documentação' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Resposta' })).toHaveCount(0)
  await page.getByRole('button', { name: UPLOAD }).click()
  const answer = page.getByRole('region', { name: 'Resposta' })
  await expect(answer).toContainText(/\bPOST\b/)
  await expect(answer).toContainText('/reports')
  await expect(answer).toContainText(/202/)
  await expect(answer).toContainText(/Location/i)
  await expect(answer).toContainText(/GET/)
  const source = page.locator('#fonte-1')
  const citation = answer.getByRole('link', { name: 'Fonte 1', exact: true }).first()

  if (testInfo.project.name === 'mobile') {
    await expect(source).toBeHidden()
    await expect(page.getByRole('button', { name: 'Fontes (1)' })).toHaveAttribute('aria-expanded', 'false')
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320)
  } else {
    await expect(source).toBeVisible()
    const answerBox = await answer.boundingBox()
    const sourceBox = await source.boundingBox()
    expect(sourceBox!.x).toBeGreaterThan(answerBox!.x + answerBox!.width)
  }

  await citation.focus()
  await page.keyboard.press('Enter')
  await expect(source).toBeFocused()
  await expect(source).toHaveAttribute('data-selected', 'true')
  await expect(source).toContainText('Envio e acompanhamento')
  await expect(source).toContainText('multipart/form-data')
  await source.getByRole('button', { name: 'Voltar à citação' }).click()
  await expect(citation).toBeFocused()
  await source.getByRole('link', { name: 'Abrir seção original' }).click()
  await expect(page).toHaveURL(SECTION)
  await expect(page.locator(':target')).toHaveText('Envio e acompanhamento')
})

test('informa que o guia não tem evidência para SSO', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: SSO }).click()
  await expect(page.getByRole('region', { name: 'Resultado da busca' }))
    .toHaveText('Não encontrei evidência suficiente no guia para responder a esta pergunta.')
  await expect(page.getByRole('heading', { name: 'Resposta' })).toHaveCount(0)
  await expect(page.getByRole('textbox', { name: 'Sua pergunta' })).toHaveValue(SSO)
})

test('preserva a pergunta durante um 503 e refaz a busca', async ({ page }) => {
  const questions: string[] = []
  await page.route('**/api/ask', async (route) => {
    questions.push(route.request().postDataJSON().question)
    if (questions.length === 1) {
      await expect(page.getByRole('region', { name: 'Resultado da busca' }))
        .toHaveText('Consultando a documentação…')
      await route.fulfill({
        status: 503,
        json: {
          status: 'temporarily_unavailable',
          message: 'A busca está temporariamente indisponível.',
          retryable: true,
        },
      })
    } else {
      await route.continue()
    }
  })
  await page.goto('/')
  const input = page.getByRole('textbox', { name: 'Sua pergunta' })
  await input.fill(UPLOAD)
  await input.press('Enter')
  const notice = page.getByRole('region', { name: 'Resultado da busca' })
  await expect(notice).toContainText('A busca está temporariamente indisponível.')
  await expect(input).toHaveValue(UPLOAD)
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('region', { name: 'Resposta' })).toContainText(/\bPOST\b/)
  expect(questions).toEqual([UPLOAD, UPLOAD])
})
