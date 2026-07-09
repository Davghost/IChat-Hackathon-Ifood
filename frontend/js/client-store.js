document.addEventListener('DOMContentLoaded', async () => {
  const guestState = document.getElementById('clientGuestState')
  const accessState = document.getElementById('clientAccessState')
  const content = document.getElementById('clientContent')
  const statusMessage = document.getElementById('clientStatusMessage')
  const clientIdentity = document.getElementById('clientIdentity')
  const logoutButton = document.getElementById('logoutButton')

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
    setMessage('A API atual nao expoe mais as rotas de cliente /users/restaurants e /users/orders.', 'error')
  } catch (error) {
    if (error?.response?.status === 401 || error?.response?.status === 422) {
      App.logout()
      showLoginState('Sua sessao expirou. Entre novamente.')
      return
    }

    show(content)
    setMessage(error?.response?.data?.msg || 'Nao foi possivel carregar a vitrine.', 'error')
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
      <p>Esta vitrine dependia de rotas de cliente que nao existem mais no backend atual.</p>
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
