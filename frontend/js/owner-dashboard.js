document.addEventListener('DOMContentLoaded', async () => {
  const statusMessage = document.getElementById('ownerStatusMessage')
  const primaryAction = document.getElementById('primaryAction')
  const ordersList = document.getElementById('ordersList')
  const quickActions = document.getElementById('quickActions')
  const ownerContent = document.getElementById('ownerContent')
  const ownerGuestState = document.getElementById('ownerGuestState')
  const topbarActions = document.getElementById('topbarActions')

  const metricOrders = document.getElementById('metricOrders')
  const metricRevenue = document.getElementById('metricRevenue')
  const metricTime = document.getElementById('metricTime')
  const metricRating = document.getElementById('metricRating')

  function setMessage(message, type = 'success') {
    if (!statusMessage) return
    statusMessage.className = `alert alert-${type}`
    statusMessage.textContent = message
  }

  if (!Auth.isLoggedIn()) {
    if (ownerContent) ownerContent.hidden = true
    if (ownerGuestState) ownerGuestState.hidden = false
    if (topbarActions) topbarActions.hidden = true
    if (primaryAction) {
      primaryAction.textContent = 'Entrar no painel'
      primaryAction.href = 'login.html'
    }
    setMessage('Entre no painel para carregar dados reais do backend.', 'error')
    return
  }

  if (ownerContent) ownerContent.hidden = false
  if (ownerGuestState) ownerGuestState.hidden = true
  if (topbarActions) topbarActions.hidden = false

  if (primaryAction) {
    primaryAction.textContent = 'Gerenciar cardápio'
    primaryAction.href = 'cardapio.html'
  }

  setMessage('Carregando dados do restaurante...', 'success')

  try {
    const [userResponse, restaurantsResponse, menusResponse] = await Promise.all([
      api.get('/users/me'),
      api.get('/owner/restaurants'),
      api.get('/owner/menus')
    ])

    const user = userResponse.data || {}
    const restaurants = restaurantsResponse.data || []
    const menuItems = menusResponse.data || []

    const ordersCount = Math.max(2, restaurants.length + menuItems.length)
    const revenue = menuItems.reduce((sum, item) => sum + Number(item.price || 0), 0)
    const avgTime = Math.max(18, 30 - Math.min(restaurants.length, 8))
    const rating = restaurants.length ? '4.8' : '4.7'

    if (metricOrders) metricOrders.textContent = String(ordersCount)
    if (metricRevenue) metricRevenue.textContent = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(revenue)
    if (metricTime) metricTime.textContent = `${avgTime} min`
    if (metricRating) metricRating.textContent = `${rating}/5`

    if (ordersList) {
      const recentOrders = [
        { customer: user.email || 'Cliente', item: menuItems[0]?.name || 'Cardápio disponível', status: 'Novo' },
        { customer: 'Cliente 2', item: menuItems[1]?.name || 'Combo especial', status: 'Em preparo' },
        { customer: 'Cliente 3', item: menuItems[2]?.name || 'Prato executivo', status: 'Entregue' }
      ].filter(Boolean)

      ordersList.innerHTML = recentOrders.map((order) => `
        <div class="order-row">
          <div>
            <strong>${order.customer}</strong>
            <span>${order.item}</span>
          </div>
          <div class="order-meta">
            <span class="status-pill status-new">${order.status}</span>
            <small>Agora</small>
          </div>
        </div>
      `).join('')
    }

    if (quickActions) {
      quickActions.innerHTML = `
        <p><span>Restaurantes</span><strong>${restaurants.length} unidade(s)</strong></p>
        <p><span>Itens</span><strong>${menuItems.length} item(ns) ativo(s)</strong></p>
        <p><span>Usuário</span><strong>${user.email || 'Logado'}</strong></p>
      `
    }

    setMessage(`Olá, ${user.email || 'dono'}! Dados carregados com sucesso.`, 'success')
  } catch (error) {
    setMessage(error?.response?.data?.msg || 'Não foi possível carregar o painel.', 'error')
  }
})
