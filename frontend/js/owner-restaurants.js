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
  const detailsCard = document.getElementById('restaurantDetailsCard')
  const deleteButton = document.getElementById('restaurantDeleteButton')

  let restaurant = null
  let menus = []

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  cancelButton?.addEventListener('click', fillForm)
  deleteButton?.addEventListener('click', removeRestaurant)

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
    setAlert('Carregando restaurante...', 'success')
    const [restaurantResponse, menusResponse] = await Promise.all([
      api.get('/owner/restaurant').catch((error) => {
        if (error?.response?.status === 404) {
          return { data: null }
        }
        throw error
      }),
      api.get('/owner/menus')
    ])

    restaurant = restaurantResponse.data || null
    menus = menusResponse.data || []
    fillForm()
    renderDetails()
    setAlert('Restaurante conectado ao backend.', 'success')
  }

  function renderDetails() {
    if (!detailsCard) {
      return
    }

    if (!restaurant) {
      detailsCard.innerHTML = `
        <div>
          <h3>Nenhum restaurante cadastrado</h3>
          <p>Cadastre o restaurante do owner. A partir dessa regra, cada owner pode ter apenas uma unidade.</p>
          <small>${menus.length} item(ns) de cardapio sem restaurante nao sao permitidos.</small>
        </div>
      `
      deleteButton.hidden = true
      return
    }

    detailsCard.innerHTML = `
        <div>
          <h3>${App.escapeHtml(restaurant.name)}</h3>
          <p>${App.escapeHtml(restaurant.description)}</p>
          <small>${countItems()} item(ns) vinculados</small>
        </div>
    `
    deleteButton.hidden = false
  }

  function countItems() {
    return restaurant ? menus.filter((item) => item.restaurant_id === restaurant.id).length : 0
  }

  async function removeRestaurant() {
    if (!restaurant || !confirm('Excluir o restaurante do owner?')) {
      return
    }

    try {
      await api.delete('/owner/restaurant')
      restaurant = null
      menus = []
      fillForm()
      renderDetails()
      setAlert('Restaurante removido.', 'success')
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel excluir o restaurante.', 'error')
    }
  }

  async function onSubmit(event) {
    event.preventDefault()

    const payload = {
      name: nameInput.value.trim(),
      description: descriptionInput.value.trim()
    }

    try {
      if (restaurant) {
        const response = await api.put('/owner/restaurant', payload)
        restaurant = response.data
        setAlert('Restaurante atualizado.', 'success')
      } else {
        const response = await api.post('/owner/restaurant', payload)
        restaurant = response.data
        setAlert('Restaurante criado.', 'success')
      }

      fillForm()
      renderDetails()
    } catch (error) {
      setAlert(error?.response?.data?.msg || 'Nao foi possivel salvar o restaurante.', 'error')
    }
  }

  function fillForm() {
    if (!restaurant) {
      form?.reset()
      formTitle.textContent = 'Cadastrar restaurante'
      saveButton.textContent = 'Criar restaurante'
      return
    }

    formTitle.textContent = 'Editar restaurante'
    saveButton.textContent = 'Salvar restaurante'
    nameInput.value = restaurant.name
    descriptionInput.value = restaurant.description
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
