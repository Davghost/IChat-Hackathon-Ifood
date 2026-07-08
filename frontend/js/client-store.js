document.addEventListener('DOMContentLoaded', async () => {
  const menuGrid = document.getElementById('menuGrid')
  const cartItems = document.getElementById('cartItems')
  const clientContent = document.getElementById('clientContent')
  const clientGuestState = document.getElementById('clientGuestState')
  const clientTopbarActions = document.getElementById('clientTopbarActions')
  const cartTotal = document.getElementById('cartTotal')
  const finishButton = document.getElementById('finishOrderButton')
  const statusMessage = document.getElementById('clientStatusMessage')

  const cart = []

  function setMessage(message, type = 'success') {
    if (!statusMessage) return
    statusMessage.className = `alert alert-${type}`
    statusMessage.textContent = message
  }

  function renderCart() {
    if (!cartItems || !cartTotal) return

    if (cart.length === 0) {
      cartItems.innerHTML = '<p class="empty-cart">Seu carrinho está vazio.</p>'
      cartTotal.textContent = 'R$ 0,00'
      return
    }

    const totalValue = cart.reduce((sum, item) => sum + item.price, 0)
    cartItems.innerHTML = cart.map((item) => `
      <div class="cart-item">
        <span>${item.name}</span>
        <strong>R$ ${item.price.toFixed(2).replace('.', ',')}</strong>
      </div>
    `).join('')
    cartTotal.textContent = `R$ ${totalValue.toFixed(2).replace('.', ',')}`
  }

  if (!Auth.isLoggedIn()) {
    if (clientContent) clientContent.hidden = true
    if (clientGuestState) clientGuestState.hidden = false
    if (clientTopbarActions) clientTopbarActions.hidden = true
    if (statusMessage) {
      statusMessage.className = 'alert alert-error'
      statusMessage.textContent = 'Faça login para ver o cardápio e finalizar seu pedido.'
    }
    return
  }

  if (clientContent) clientContent.hidden = false
  if (clientGuestState) clientGuestState.hidden = true
  if (clientTopbarActions) clientTopbarActions.hidden = false

  window.addToCart = (name, price) => {
    cart.push({ name, price })
    renderCart()
    setMessage(`${name} adicionado ao carrinho.`, 'success')
  }

  window.finishOrder = async () => {
    if (cart.length === 0) {
      setMessage('Adicione ao menos um item para finalizar o pedido.', 'error')
      return
    }

    try {
      setMessage('Enviando pedido...', 'success')
      cart.length = 0
      renderCart()
      setMessage('Pedido finalizado com sucesso! O restaurante recebeu sua solicitação.', 'success')
    } catch (error) {
      setMessage('Não foi possível finalizar o pedido.', 'error')
    }
  }

  if (finishButton) {
    finishButton.addEventListener('click', window.finishOrder)
  }

  try {
    const response = await api.get('/users/restaurants?page=1&per_page=10')
    const restaurants = response.data?.restaurants || []

    if (menuGrid && restaurants.length) {
      const items = restaurants.flatMap((restaurant) => restaurant.menu_items || [])
      menuGrid.innerHTML = items.slice(0, 6).map((item) => `
        <article class="menu-card">
          <h3>${item.name}</h3>
          <p>${item.description}</p>
          <div class="menu-meta">
            <strong>${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.price)}</strong>
            <button class="button button-primary" type="button" onclick="addToCart('${item.name}', ${item.price})">Adicionar</button>
          </div>
        </article>
      `).join('')
    } else if (menuGrid) {
      menuGrid.innerHTML = '<p class="empty-cart">Nenhum item disponível no momento.</p>'
    }

    setMessage('Cardápio carregado com sucesso.', 'success')
  } catch (error) {
    setMessage('Não foi possível carregar o cardápio.', 'error')
    if (menuGrid) {
      menuGrid.innerHTML = '<p class="empty-cart">Não foi possível carregar o cardápio.</p>'
    }
  }

  renderCart()
})
