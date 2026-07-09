document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('pageAccessState')
  const content = document.getElementById('ordersPageContent')
  const alertBox = document.getElementById('pageAlert')
  const userBadge = document.getElementById('sidebarUserBadge')
  const logoutButton = document.getElementById('logoutButton')
  const statusFilter = document.getElementById('statusFilter')
  const applyFiltersButton = document.getElementById('applyFiltersButton')
  const metrics = document.getElementById('ordersStatusMetrics')
  const ordersBoard = document.getElementById('ordersBoard')

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  hide(content)
  hide(guestState)

  if (!Auth.isLoggedIn()) {
    showState(guestState, 'Entre para acompanhar os pedidos da operacao.', 'Ir para login', 'login.html')
    return
  }

  try {
    const user = await App.getCurrentUser()
    userBadge.textContent = user?.email || 'Sessao ativa'

    if (user?.role !== 'owner') {
      showState(
        guestState,
        'Os pedidos desta operacao sao exclusivos da conta owner.',
        'Abrir area do cliente',
        'homeclient.html'
      )
      return
    }

    show(content)
    applyFiltersButton?.addEventListener('click', loadOrders)
    await loadOrders()
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showState(guestState, 'Sua sessao expirou. Entre novamente.', 'Ir para login', 'login.html')
      return
    }

    show(content)
    setAlert(error?.response?.data?.msg || 'Nao foi possivel carregar os pedidos.', 'error')
  }

  async function loadOrders() {
    setAlert('Carregando pedidos...', 'success')

    const params = new URLSearchParams({
      page: '1',
      per_page: '12',
      days: '30'
    })
    
    if (statusFilter.value) {
      
    }

    try {
      const response = await api.get(`/owner/orders?${params.toString()}`)
      const page = response.data || {}
      renderStatusCounts(page.status_counts || [])
      renderOrders(page.orders || [])
      setAlert('Pedidos carregados com dados reais do backend.', 'success')
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel filtrar os pedidos.', 'error')
    }
  }

  function renderStatusCounts(statusCounts) {
    metrics.innerHTML = statusCounts.map((item) => `
      <article class="metric-card metric-red compact-metric">
        <span>${App.statusLabel(item.status)}</span>
        <strong>${item.count}</strong>
        <small>Status atual</small>
      </article>
    `).join('')
  }

  function renderOrders(orders) {
    if (!orders.length) {
      ordersBoard.innerHTML = '<p class="empty-cart">Nenhum pedido encontrado com os filtros atuais.</p>'
      return
    }

    ordersBoard.innerHTML = orders.map((order) => `
      <article class="order-card">
        <div class="order-card-top">
          <div>
            <h3>${App.escapeHtml(order.customer?.name || 'Cliente')}</h3>
          </div>
          <span class="status-pill ${App.statusClass(order.status)}">${App.statusLabel(order.status)}</span>
        </div>
        <p>${App.escapeHtml(order.main_dish || 'Item sem nome')}</p>
        <div class="order-card-bottom">
          <small>${App.formatDateTime(order.order_time)}</small>
          <strong>${App.formatCurrency(order.total_price)}</strong>
        </div>
        <div class="inline-form">
          <select data-status="${order.id}">
            ${renderStatusOptions(order.status)}
          </select>
          <button class="button button-primary small-button" type="button" data-save="${order.id}">Atualizar</button>
        </div>
      </article>
    `).join('')

    ordersBoard.querySelectorAll('[data-save]').forEach((button) => {
      button.addEventListener('click', () => updateStatus(Number(button.dataset.save)))
    })
  }

  function renderStatusOptions(selectedStatus) {
    return ['new', 'preparing', 'ready', 'delivered', 'cancelled'].map((status) => `
      <option value="${status}" ${status === selectedStatus ? 'selected' : ''}>${App.statusLabel(status)}</option>
    `).join('')
  }

  async function updateStatus(orderId) {
    const select = ordersBoard.querySelector(`[data-status="${orderId}"]`)
    if (!select) {
      return
    }

    try {
      await api.patch(`/owner/orders/${orderId}/status`, {
        status: select.value
      })
      setAlert('Status atualizado.', 'success')
      await loadOrders()
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel atualizar o status.', 'error')
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
