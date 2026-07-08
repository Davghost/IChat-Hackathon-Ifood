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
  const aiMetrics = document.getElementById('aiMetrics')
  const aiInsights = document.getElementById('aiInsights')

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

    const [historyResponse, forecastResponse, aiPlaceholderResponse] = await Promise.all([
      api.get('/owner/analytics/history?days=30'),
      api.get('/owner/forecasts?days=7'),
      api.get('/owner/ai/placeholders?days=30')
    ])

    const history = historyResponse.data || {}
    const summary = history.summary || {}
    const charts = history.charts || []
    const forecasts = forecastResponse.data?.forecasts || []
    const placeholderPayload = aiPlaceholderResponse.data || {}
    const placeholderMetrics = placeholderPayload.metrics || []
    const placeholderInsights = placeholderPayload.insights || []
    const placeholderNote = placeholderPayload.placeholder_note || 'PLACEHOLDER'

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

    aiMetrics.innerHTML = placeholderMetrics.length
      ? placeholderMetrics.map((item) => `
          <p>
            <span>${App.escapeHtml(item.label || 'PLACEHOLDER')}</span>
            <strong>${App.escapeHtml(item.value || '')}</strong>
          </p>
        `).join('')
      : '<p class="empty-cart">Sem placeholders de IA disponiveis.</p>'

    aiInsights.innerHTML = placeholderInsights.length
      ? `
          <strong>${App.escapeHtml(placeholderNote)}</strong>
          ${placeholderInsights.map((item) => `
            <p><strong>${App.escapeHtml(item.title || 'PLACEHOLDER')}</strong></p>
            <p>${App.escapeHtml(item.description || '')}</p>
          `).join('')}
        `
      : `
          <strong>${App.escapeHtml(placeholderNote)}</strong>
          <p>Os insights de IA ainda nao foram implementados.</p>
        `

    setAlert('Faturamento, previsoes e placeholders de IA carregados.', 'success')
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
  return points.slice(-7).map((point) => {
    const height = Math.max(18, Math.round((Number(point.revenue || 0) / max) * 100))
    return `
      <span style="height:${height}%">
        <small>${App.escapeHtml(point.date.slice(5))}</small>
      </span>
    `
  }).join('')
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
