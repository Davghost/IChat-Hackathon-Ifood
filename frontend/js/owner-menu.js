document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('pageAccessState')
  const content = document.getElementById('menuPageContent')
  const alertBox = document.getElementById('pageAlert')
  const userBadge = document.getElementById('sidebarUserBadge')
  const logoutButton = document.getElementById('logoutButton')
  const form = document.getElementById('menuForm')
  const titleInput = document.getElementById('menuTitle')
  const nameInput = document.getElementById('menuName')
  const priceInput = document.getElementById('menuPrice')
  const descriptionInput = document.getElementById('menuDescription')
  const restaurantBadge = document.getElementById('restaurantBadge')
  const formTitle = document.getElementById('menuFormTitle')
  const saveButton = document.getElementById('menuSaveButton')
  const cancelButton = document.getElementById('menuCancelButton')
  const tableBody = document.getElementById('menuTableBody')

  let restaurant = null
  let items = []
  let editingId = null

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  cancelButton?.addEventListener('click', resetForm)

  hide(content)
  hide(guestState)

  if (!Auth.isLoggedIn()) {
    showLoginState(guestState, 'Entre para gerenciar o cardapio.')
    return
  }

  try {
    const user = await App.getCurrentUser()
    userBadge.textContent = user?.email || 'Sessao ativa'

    if (user?.role !== 'owner') {
      showRoleState(guestState, 'Somente contas owner podem editar o cardapio.')
      return
    }

    show(content)
    await loadData()
    form?.addEventListener('submit', onSubmit)
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showLoginState(guestState, 'Sua sessao expirou. Entre novamente.')
      return
    }

    show(content)
    setAlert(error?.response?.data?.msg || 'Nao foi possivel carregar o cardapio.', 'error')
  }

  async function loadData() {
    setAlert('Carregando restaurante e itens...', 'success')
    const [restaurantResponse, itemsResponse] = await Promise.all([
      api.get('/owner/restaurant').catch((error) => {
        if (error?.response?.status === 404) {
          return { data: null }
        }
        throw error
      }),
      api.get('/owner/menus')
    ])

    restaurant = restaurantResponse.data || null
    items = itemsResponse.data || []

    renderRestaurantBadge()
    renderItems()

    if (!restaurant) {
      setAlert('Cadastre o restaurante primeiro. Cada owner agora pode ter apenas uma unidade.', 'error')
      saveButton.disabled = true
    } else {
      saveButton.disabled = false
      setAlert('Cardapio conectado ao backend.', 'success')
    }
  }

  function renderRestaurantBadge() {
    if (!restaurantBadge) {
      return
    }

    restaurantBadge.textContent = restaurant ? restaurant.name : 'Nenhum restaurante cadastrado'
  }

  function renderItems() {
    if (!tableBody) {
      return
    }

    if (!items.length) {
      tableBody.innerHTML = `
        <div class="table-row">
          <div>
            <strong>Nenhum item cadastrado</strong>
            <small>Use o formulario acima para criar o primeiro item.</small>
          </div>
          <span>-</span>
          <span>-</span>
          <span>-</span>
        </div>
      `
      return
    }

    tableBody.innerHTML = items.map((item) => `
      <div class="table-row">
        <div>
          <strong>${App.escapeHtml(item.name)}</strong>
          <small>${App.escapeHtml(item.description)}</small>
        </div>
        <span>${App.escapeHtml(item.title)}</span>
        <span>${App.formatCurrency(item.price)}</span>
        <div class="row-actions">
          <button class="button button-ghost small-button" type="button" data-edit="${item.id}">Editar</button>
          <button class="button button-ghost small-button danger-text" type="button" data-delete="${item.id}">Excluir</button>
        </div>
      </div>
    `).join('')

    tableBody.querySelectorAll('[data-edit]').forEach((button) => {
      button.addEventListener('click', () => startEdit(Number(button.dataset.edit)))
    })

    tableBody.querySelectorAll('[data-delete]').forEach((button) => {
      button.addEventListener('click', () => removeItem(Number(button.dataset.delete)))
    })
  }

  function startEdit(id) {
    const item = items.find((entry) => entry.id === id)
    if (!item) {
      return
    }

    editingId = id
    formTitle.textContent = 'Editar item'
    titleInput.value = item.title
    nameInput.value = item.name
    priceInput.value = item.price
    descriptionInput.value = item.description
    saveButton.textContent = 'Salvar item'
  }

  async function removeItem(id) {
    if (!confirm('Excluir este item do cardapio?')) {
      return
    }

    try {
      await api.delete(`/owner/menus/${id}`)
      items = items.filter((item) => item.id !== id)
      renderItems()
      if (editingId === id) {
        resetForm()
      }
      setAlert('Item removido.', 'success')
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel excluir o item.', 'error')
    }
  }

  async function onSubmit(event) {
    event.preventDefault()

    if (!restaurant) {
      setAlert('Cadastre o restaurante antes de salvar itens.', 'error')
      return
    }

    const payload = {
      title: titleInput.value.trim(),
      name: nameInput.value.trim(),
      price: Number(priceInput.value),
      description: descriptionInput.value.trim()
    }

    try {
      if (editingId) {
        const response = await api.put(`/owner/menus/${editingId}`, payload)
        items = items.map((item) => item.id === editingId ? response.data : item)
        setAlert('Item atualizado.', 'success')
      } else {
        const response = await api.post('/owner/menus', payload)
        items = [response.data, ...items]
        setAlert('Item criado.', 'success')
      }

      resetForm()
      renderItems()
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel salvar o item.', 'error')
    }
  }

  function resetForm() {
    editingId = null
    form?.reset()
    formTitle.textContent = 'Novo item'
    saveButton.textContent = 'Criar item'
    renderRestaurantBadge()
  }

  function setAlert(message, type) {
    if (!alertBox) {
      return
    }

    alertBox.className = `alert alert-${type}`
    alertBox.textContent = message
  }
})

function showLoginState(element, message) {
  element.innerHTML = `
    <h2>Entre para continuar</h2>
    <p>${App.escapeHtml(message)}</p>
    <a class="button button-primary" href="login.html">Ir para login</a>
  `
  element.hidden = false
}

function showRoleState(element, message) {
  element.innerHTML = `
    <h2>Acesso do owner necessario</h2>
    <p>${App.escapeHtml(message)}</p>
    <a class="button button-primary" href="homeclient.html">Abrir area do cliente</a>
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
