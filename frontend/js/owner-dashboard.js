document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('ownerGuestState')
  const accessState = document.getElementById('ownerAccessState')
  const content = document.getElementById('ownerContent')
  const alertBox = document.getElementById('ownerStatusMessage')
  const ownerIdentity = document.getElementById('ownerIdentity')
  const logoutButton = document.getElementById('logoutButton')

  const metricOrders = document.getElementById('metricOrders')
  const metricRevenue = document.getElementById('metricRevenue')
  const metricItems = document.getElementById('metricItems')
  const metricTicket = document.getElementById('metricTicket')
  const ordersList = document.getElementById('ordersList')
  const topItems = document.getElementById('topItems')
  const ordersChart = document.getElementById('ordersChart')
  const revenueChart = document.getElementById('revenueChart')

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  hide(accessState)
  hide(guestState)
  hide(content)

  if (!Auth.isLoggedIn()) {
    show(guestState)
    return
  }

  try {
    const user = await App.getCurrentUser()
    ownerIdentity.textContent = user?.email || 'Sessao ativa'

    if (user?.role !== 'owner') {
      showAccessState(
        accessState,
        'Esta area e exclusiva para donos de restaurante.',
        'Abrir area do cliente',
        'homeclient.html'
      )
      return
    }

    show(content)
    setAlert('Carregando metricas e pedidos...', 'success')

    const [dashboardResponse, ordersResponse] = await Promise.all([
      api.get('/owner/dashboard?days=7'),
      api.get('/owner/orders?page=1&per_page=6&days=7')
    ])

    const dashboard = dashboardResponse.data || {}
    const summary = dashboard.summary || {}
    const charts = dashboard.charts || {}
    const orders = ordersResponse.data?.orders || []

    metricOrders.textContent = String(summary.total_orders_today || 0)
    metricRevenue.textContent = App.formatCurrency(summary.revenue_today)
    metricItems.textContent = String(summary.items_sold_today || 0)
    metricTicket.textContent = App.formatCurrency(summary.average_ticket_today)

    ordersList.innerHTML = orders.length
      ? orders.map((order) => `
          <article class="order-row">
            <div>
              <strong>#${order.id} ${App.escapeHtml(order.customer.username)}</strong>
              <span>${App.escapeHtml(order.menu_item.name)} · ${App.escapeHtml(order.restaurant.name)}</span>
            </div>
            <div class="order-meta">
              <span class="status-pill ${App.statusClass(order.status)}">${App.statusLabel(order.status)}</span>
              <strong>${App.formatCurrency(order.total_price)}</strong>
            </div>
          </article>
        `).join('')
      : '<p class="empty-cart">Nenhum pedido encontrado nos ultimos dias.</p>'

    topItems.innerHTML = (charts.top_menu_items || []).length
      ? charts.top_menu_items.map((item, index) => `
          <article class="best-item">
            <span>${String(index + 1).padStart(2, '0')}</span>
            <div>
              <strong>${App.escapeHtml(item.name)}</strong>
              <small>${item.quantity} vendidos</small>
            </div>
            <strong>${App.formatCurrency(item.revenue)}</strong>
          </article>
        `).join('')
      : '<p class="empty-cart">Sem itens vendidos no periodo.</p>'

    ordersChart.innerHTML = renderBars(
      charts.orders_by_day || [],
      'orders',
      (point) => `${point.orders} pedidos`
    )

    revenueChart.innerHTML = renderBars(
      charts.revenue_by_day || [],
      'revenue',
      (point) => App.formatCurrency(point.revenue)
    )

    setAlert('Painel carregado com dados reais do backend.', 'success')
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      show(guestState)
      return
    }

    show(content)
    setAlert(error?.response?.data?.msg || 'Nao foi possivel carregar o painel.', 'error')
  }

  function setAlert(message, type) {
    if (!alertBox) {
      return
    }

    alertBox.className = `alert alert-${type}`
    alertBox.textContent = message
  }
})

function renderBars(points, key, labelFormatter) {
  if (!points.length) {
    return '<p class="empty-cart">Sem historico suficiente para renderizar o grafico.</p>'
  }

  const values = points.map((point) => Number(point[key] || 0))
  const max = Math.max(...values, 1)

  return `
    <div class="mini-chart">
      ${points.map((point) => {
        const height = Math.max(14, Math.round((Number(point[key] || 0) / max) * 100))
        return `
          <div class="mini-bar-wrap">
            <div class="mini-bar" style="height:${height}%"></div>
            <strong>${App.escapeHtml(point.date.slice(5))}</strong>
            <small>${App.escapeHtml(labelFormatter(point))}</small>
          </div>
        `
      }).join('')}
    </div>
  `
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

function showAccessState(element, description, buttonLabel, href) {
  if (!element) {
    return
  }

  element.innerHTML = `
    <h2>Acesso indisponivel</h2>
    <p>${App.escapeHtml(description)}</p>
    <a class="button button-primary" href="${href}">${App.escapeHtml(buttonLabel)}</a>
  `
  show(element)
}
