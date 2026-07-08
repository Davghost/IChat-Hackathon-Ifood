document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('pageAccessState')
  const content = document.getElementById('analyticsPageContent')
  const alertBox = document.getElementById('pageAlert')
  const userBadge = document.getElementById('sidebarUserBadge')
  const logoutButton = document.getElementById('logoutButton')
  const revenueValue = document.getElementById('revenueValue')
  const revenueBars = document.getElementById('revenueBars')
  const financeList = document.getElementById('financeList')
  const forecastList = document.getElementById('forecastList')
  const assistantTemplates = document.getElementById('assistantTemplates')
  const assistantQuestion = document.getElementById('assistantQuestion')
  const assistantAnswer = document.getElementById('assistantAnswer')
  const askAssistantButton = document.getElementById('askAssistantButton')

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  hide(content)
  hide(guestState)

  if (!Auth.isLoggedIn()) {
    showState(guestState, 'Entre para ver faturamento, previsoes e metricas.', 'Ir para login', 'login.html')
    return
  }

  try {
    const user = await App.getCurrentUser()
    userBadge.textContent = user?.email || 'Sessao ativa'

    if (user?.role !== 'owner') {
      showState(
        guestState,
        'A area financeira e exclusiva da conta owner.',
        'Abrir area do cliente',
        'homeclient.html'
      )
      return
    }

    show(content)
    askAssistantButton?.addEventListener('click', submitQuestion)
    await loadAnalytics()
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showState(guestState, 'Sua sessao expirou. Entre novamente.', 'Ir para login', 'login.html')
      return
    }

    show(content)
    setAlert(error?.response?.data?.msg || 'Nao foi possivel carregar o faturamento.', 'error')
  }

  async function loadAnalytics() {
    setAlert('Carregando analytics...', 'success')

    const [historyResponse, forecastResponse, templatesResponse] = await Promise.all([
      api.get('/owner/analytics/history?days=30'),
      api.get('/owner/forecasts?days=7'),
      api.get('/owner/assistant/templates')
    ])

    const history = historyResponse.data || {}
    const summary = history.summary || {}
    const charts = history.charts || []
    const forecasts = forecastResponse.data?.forecasts || []
    const templates = templatesResponse.data?.questions || []

    revenueValue.textContent = App.formatCurrency(summary.total_revenue)
    revenueBars.innerHTML = renderRevenueBars(charts)
    financeList.innerHTML = `
      <p><span>Pedidos no periodo</span><strong>${summary.total_orders || 0}</strong></p>
      <p><span>Itens vendidos</span><strong>${summary.items_sold || 0}</strong></p>
      <p><span>Ticket medio</span><strong>${App.formatCurrency(summary.average_ticket)}</strong></p>
      <p><span>Melhor dia</span><strong>${App.escapeHtml(summary.best_weekday || 'Sem dados')}</strong></p>
      <p><span>Top item</span><strong>${App.escapeHtml(summary.top_menu_item?.name || 'Sem dados')}</strong></p>
    `

    forecastList.innerHTML = forecasts.length
      ? forecasts.map((item) => `
          <div class="forecast-item">
            <strong>${App.escapeHtml(item.date)}</strong>
            <span>${App.formatCurrency(item.predicted_revenue)}</span>
            <small>${item.predicted_orders} pedido(s) · ${item.predicted_items_sold} item(ns)</small>
          </div>
        `).join('')
      : '<p class="empty-cart">Sem previsao disponivel.</p>'

    assistantTemplates.innerHTML = templates.map((item) => `
      <button class="template-chip" type="button" data-question="${App.escapeHtml(item.question)}">
        ${App.escapeHtml(item.question)}
      </button>
    `).join('')

    assistantTemplates.querySelectorAll('[data-question]').forEach((button) => {
      button.addEventListener('click', () => {
        assistantQuestion.value = button.dataset.question
      })
    })

    setAlert('Faturamento, previsoes e perguntas prontas carregados.', 'success')
  }

  async function submitQuestion() {
    const question = assistantQuestion.value.trim()
    if (!question) {
      setAlert('Digite uma pergunta para o assistente.', 'error')
      return
    }

    setAlert('Consultando assistente...', 'success')

    try {
      const response = await api.post('/owner/assistant/chat', { question })
      const answer = response.data || {}
      assistantAnswer.innerHTML = `
        <strong>${App.escapeHtml(answer.answer || '')}</strong>
      `
      setAlert('Resposta recebida.', 'success')
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel consultar o assistente.', 'error')
    }
  }

  function setAlert(message, type) {
    if (!alertBox) {
      return
    }

    alertBox.className = `alert alert-${type}`
    alertBox.textContent = message
  }
})

function renderRevenueBars(points) {
  if (!points.length) {
    return '<p class="empty-cart">Sem historico suficiente para renderizar o grafico.</p>'
  }

  const max = Math.max(...points.map((point) => Number(point.revenue || 0)), 1)
  const visiblePoints = points.slice(-6)

  return `
    <div class="mini-chart">
      ${visiblePoints.map((point) => {
        const value = Number(point.revenue || 0)
        const height = Math.max(24, Math.round((value / max) * 100))
        const date = App.escapeHtml(point.date?.slice(5) || '')
        const amount = App.escapeHtml(App.formatCurrency(value))

        return `
          <div class="mini-bar-wrap">
            <div class="mini-bar-value">${amount}</div>
            <div class="mini-bar-track">
              <div class="mini-bar" style="height:${height}%; background:linear-gradient(180deg, #ff8a3d 0%, #f59f00 100%);"></div>
            </div>
            <strong>${date}</strong>
          </div>
        `
      }).join('')}
    </div>
  `
}

function showState(element, message, buttonLabel, href) {
  element.innerHTML = `
    <h2>Acesso indisponivel</h2>
    <p>${App.escapeHtml(message)}</p>
    <a class="button button-primary" href="${href}">${App.escapeHtml(buttonLabel)}</a>
  `
  element.hidden = false
}

function show(element) {
  if (element) {
    element.hidden = false
  }
}

function hide(element) {
  if (element) {
    element.hidden = true
  }
}
