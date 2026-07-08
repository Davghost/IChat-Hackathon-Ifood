document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('pageAccessState')
  const content = document.getElementById('restaurantsPageContent')
  const alertBox = document.getElementById('pageAlert')
  const userBadge = document.getElementById('sidebarUserBadge')
  const logoutButton = document.getElementById('logoutButton')
  const form = document.getElementById('restaurantForm')
  const nameInput = document.getElementById('restaurantName')
  const descriptionInput = document.getElementById('restaurantDescription')
  const formTitle = document.getElementById('restaurantFormTitle')
  const saveButton = document.getElementById('restaurantSaveButton')
  const cancelButton = document.getElementById('restaurantCancelButton')
  const cards = document.getElementById('restaurantCards')

  let restaurants = []
  let menus = []
  let editingId = null

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  cancelButton?.addEventListener('click', resetForm)

  hide(content)
  hide(guestState)

  if (!Auth.isLoggedIn()) {
    showState(guestState, 'Entre para administrar suas lojas.', 'Ir para login', 'login.html')
    return
  }

  try {
    const user = await App.getCurrentUser()
    userBadge.textContent = user?.email || 'Sessao ativa'

    if (user?.role !== 'owner') {
      showState(
        guestState,
        'Somente contas owner podem acessar a gestao de lojas.',
        'Abrir area do cliente',
        'homeclient.html'
      )
      return
    }

    show(content)
    form?.addEventListener('submit', onSubmit)
    await loadData()
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showState(guestState, 'Sua sessao expirou. Entre novamente.', 'Ir para login', 'login.html')
      return
    }

    show(content)
    setAlert(error?.response?.data?.msg || 'Nao foi possivel carregar as lojas.', 'error')
  }

  async function loadData() {
    setAlert('Carregando lojas...', 'success')
    const [restaurantsResponse, menusResponse] = await Promise.all([
      api.get('/owner/restaurants'),
      api.get('/owner/menus')
    ])

    restaurants = restaurantsResponse.data || []
    menus = menusResponse.data || []
    renderCards()
    setAlert('Lojas conectadas ao backend.', 'success')
  }

  function renderCards() {
    if (!cards) {
      return
    }

    if (!restaurants.length) {
      cards.innerHTML = `
        <article class="restaurant-card">
          <div class="restaurant-avatar">+</div>
          <div>
            <h3>Nenhuma loja cadastrada</h3>
            <p>Crie sua primeira unidade para vincular cardapio, pedidos e faturamento.</p>
            <small>Use o formulario acima</small>
          </div>
        </article>
      `
      return
    }

    cards.innerHTML = restaurants.map((restaurant) => `
      <article class="restaurant-card">
        <div class="restaurant-avatar">${App.initials(restaurant.name)}</div>
        <div>
          <h3>${App.escapeHtml(restaurant.name)}</h3>
          <p>${App.escapeHtml(restaurant.description)}</p>
          <small>${countItems(restaurant.id)} item(ns) vinculados</small>
        </div>
        <div class="row-actions">
          <button class="button button-ghost small-button" type="button" data-edit="${restaurant.id}">Editar</button>
          <button class="button button-ghost small-button danger-text" type="button" data-delete="${restaurant.id}">Excluir</button>
        </div>
      </article>
    `).join('')

    cards.querySelectorAll('[data-edit]').forEach((button) => {
      button.addEventListener('click', () => startEdit(Number(button.dataset.edit)))
    })

    cards.querySelectorAll('[data-delete]').forEach((button) => {
      button.addEventListener('click', () => removeRestaurant(Number(button.dataset.delete)))
    })
  }

  function countItems(restaurantId) {
    return menus.filter((item) => item.restaurant_id === restaurantId).length
  }

  function startEdit(id) {
    const restaurant = restaurants.find((entry) => entry.id === id)
    if (!restaurant) {
      return
    }

    editingId = id
    formTitle.textContent = 'Editar loja'
    nameInput.value = restaurant.name
    descriptionInput.value = restaurant.description
    saveButton.textContent = 'Salvar loja'
  }

  async function removeRestaurant(id) {
    if (!confirm('Excluir esta loja?')) {
      return
    }

    try {
      await api.delete(`/owner/restaurants/${id}`)
      restaurants = restaurants.filter((restaurant) => restaurant.id !== id)
      menus = menus.filter((item) => item.restaurant_id !== id)
      renderCards()
      if (editingId === id) {
        resetForm()
      }
      setAlert('Loja removida.', 'success')
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel excluir a loja.', 'error')
    }
  }

  async function onSubmit(event) {
    event.preventDefault()

    const payload = {
      name: nameInput.value.trim(),
      description: descriptionInput.value.trim()
    }

    try {
      if (editingId) {
        const response = await api.put(`/owner/restaurants/${editingId}`, payload)
        restaurants = restaurants.map((restaurant) => restaurant.id === editingId ? response.data : restaurant)
        setAlert('Loja atualizada.', 'success')
      } else {
        const response = await api.post('/owner/restaurants', payload)
        restaurants = [response.data, ...restaurants]
        setAlert('Loja criada.', 'success')
      }

      resetForm()
      renderCards()
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel salvar a loja.', 'error')
    }
  }

  function resetForm() {
    editingId = null
    form?.reset()
    formTitle.textContent = 'Nova loja'
    saveButton.textContent = 'Criar loja'
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
