document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('clientGuestState')
  const accessState = document.getElementById('clientAccessState')
  const content = document.getElementById('clientContent')
  const statusMessage = document.getElementById('clientStatusMessage')
  const clientIdentity = document.getElementById('clientIdentity')
  const logoutButton = document.getElementById('logoutButton')
  const restaurantTabs = document.getElementById('restaurantTabs')
  const menuGrid = document.getElementById('menuGrid')
  const cartItems = document.getElementById('cartItems')
  const cartTotal = document.getElementById('cartTotal')
  const finishButton = document.getElementById('finishOrderButton')

  let restaurants = []
  let cart = []
  let selectedRestaurantId = null

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  hide(guestState)
  hide(accessState)
  hide(content)

  if (!Auth.isLoggedIn()) {
    showLoginState()
    return
  }

  try {
    const user = await App.getCurrentUser()
    clientIdentity.textContent = user?.email || 'Sessao ativa'

    if (user?.role === 'owner') {
      showAccessState()
      return
    }

    show(content)
    finishButton?.addEventListener('click', finishOrder)
    await loadRestaurants()
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showLoginState('Sua sessao expirou. Entre novamente.')
      return
    }

    show(content)
    setMessage(error?.response?.data?.msg || 'Nao foi possivel carregar a vitrine.', 'error')
  }

  async function loadRestaurants() {
    setMessage('Carregando restaurantes e cardapio...', 'success')
    const response = await api.get('/users/restaurants?page=1&per_page=20')
    restaurants = response.data?.restaurants || []
    selectedRestaurantId = restaurants[0]?.id || null

    renderRestaurantTabs()
    renderMenu()
    renderCart()
    setMessage('Vitrine conectada aos restaurantes disponiveis.', 'success')
  }

  function renderRestaurantTabs() {
    if (!restaurantTabs) {
      return
    }

    if (!restaurants.length) {
      restaurantTabs.innerHTML = '<p class="empty-cart">Nenhuma loja disponivel no momento.</p>'
      return
    }

    restaurantTabs.innerHTML = restaurants.map((restaurant) => `
      <button class="tab-chip ${restaurant.id === selectedRestaurantId ? 'active' : ''}" type="button" data-restaurant="${restaurant.id}">
        ${App.escapeHtml(restaurant.name)}
      </button>
    `).join('')

    restaurantTabs.querySelectorAll('[data-restaurant]').forEach((button) => {
      button.addEventListener('click', () => {
        selectedRestaurantId = Number(button.dataset.restaurant)
        renderRestaurantTabs()
        renderMenu()
      })
    })
  }

  function renderMenu() {
    if (!menuGrid) {
      return
    }

    const restaurant = restaurants.find((item) => item.id === selectedRestaurantId)
    const items = restaurant?.menu_items || []

    if (!items.length) {
      menuGrid.innerHTML = '<p class="empty-cart">Esta loja ainda nao publicou itens. Escolha outra unidade.</p>'
      return
    }

    menuGrid.innerHTML = items.map((item) => `
      <article class="menu-card">
        <span class="eyebrow">${App.escapeHtml(item.title)}</span>
        <h3>${App.escapeHtml(item.name)}</h3>
        <p>${App.escapeHtml(item.description)}</p>
        <div class="menu-meta">
          <strong>${App.formatCurrency(item.price)}</strong>
          <button class="button button-primary small-button" type="button" data-add="${item.id}">Adicionar</button>
        </div>
      </article>
    `).join('')

    menuGrid.querySelectorAll('[data-add]').forEach((button) => {
      button.addEventListener('click', () => addToCart(Number(button.dataset.add)))
    })
  }

  function addToCart(menuItemId) {
    const item = restaurants
      .flatMap((restaurant) => restaurant.menu_items || [])
      .find((menuItem) => menuItem.id === menuItemId)

    if (!item) {
      return
    }

    cart.push({
      menu_item_id: item.id,
      name: item.name,
      price: Number(item.price || 0)
    })
    renderCart()
    setMessage(`${item.name} adicionado ao carrinho.`, 'success')
  }

  function renderCart() {
    if (!cartItems || !cartTotal) {
      return
    }

    if (!cart.length) {
      cartItems.innerHTML = '<p class="empty-cart">Seu carrinho esta vazio.</p>'
      cartTotal.textContent = App.formatCurrency(0)
      return
    }

    const total = cart.reduce((sum, item) => sum + item.price, 0)
    const groupedNames = Object.values(cart.reduce((accumulator, item) => {
      const key = item.menu_item_id
      if (!accumulator[key]) {
        accumulator[key] = { ...item, quantity: 0 }
      }
      accumulator[key].quantity += 1
      return accumulator
    }, {}))

    cartItems.innerHTML = groupedNames.map((item) => `
      <div class="cart-item">
        <span>${App.escapeHtml(item.name)} x${item.quantity}</span>
        <strong>${App.formatCurrency(item.price * item.quantity)}</strong>
      </div>
    `).join('')

    cartTotal.textContent = App.formatCurrency(total)
  }

  async function finishOrder() {
    if (!cart.length) {
      setMessage('Adicione pelo menos um item para finalizar.', 'error')
      return
    }

    const grouped = App.groupCartItems(cart)
    setMessage('Enviando pedido para o backend...', 'success')

    try {
      await Promise.all(grouped.map((item) => api.post('/users/orders', item)))
      cart = []
      renderCart()
      setMessage('Pedido enviado com sucesso. Historico detalhado ainda sera implementado para o cliente.', 'success')
    } catch (error) {
      setMessage(error?.response?.data?.msg || 'Nao foi possivel concluir o pedido.', 'error')
    }
  }

  function setMessage(message, type) {
    if (!statusMessage) {
      return
    }

    statusMessage.className = `alert alert-${type}`
    statusMessage.textContent = message
  }

  function showLoginState(message = 'Faca login para ver o cardapio e fazer pedidos.') {
    guestState.hidden = false
    guestState.innerHTML = `
      <h2>Entre para pedir</h2>
      <p>${App.escapeHtml(message)}</p>
      <a class="button button-primary" href="login.html">Ir para login</a>
    `
  }

  function showAccessState() {
    accessState.hidden = false
    accessState.innerHTML = `
      <h2>Conta owner detectada</h2>
      <p>Esta vitrine e voltada ao fluxo de cliente. Sua conta possui recursos de gestao.</p>
      <a class="button button-primary" href="homeowner.html">Abrir painel do owner</a>
    `
  }
})

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
