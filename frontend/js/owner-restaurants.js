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

  logoutButton?.addEventListener('click', () => {
    App.logout()
    location.href = 'login.html'
  })

  cancelButton?.addEventListener('click', () => form?.reset())

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
    renderUnavailableState()
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showState(guestState, 'Sua sessao expirou. Entre novamente.', 'Ir para login', 'login.html')
      return
    }

    show(content)
    setAlert(error?.response?.data?.msg || 'Nao foi possivel carregar as lojas.', 'error')
  }

  function renderUnavailableState() {
    if (detailsCard) {
      detailsCard.innerHTML = `
        <div>
          <h3>Gestao de restaurante indisponivel</h3>
          <p>O backend atual nao expoe mais as rotas /owner/restaurant nem /owner/menus.</p>
          <small>A tela foi ajustada para nao consumir endpoints removidos.</small>
        </div>
      `
    }

    if (deleteButton) {
      deleteButton.hidden = true
      deleteButton.disabled = true
    }

    if (formTitle) {
      formTitle.textContent = 'Gestao indisponivel'
    }

    ;[nameInput, descriptionInput].forEach((input) => {
      if (input) {
        input.disabled = true
      }
    })

    if (saveButton) {
      saveButton.disabled = true
      saveButton.textContent = 'Indisponivel'
    }

    setAlert('Rotas de restaurante removidas do backend. Esta tela nao faz mais chamadas inexistentes.', 'error')
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
