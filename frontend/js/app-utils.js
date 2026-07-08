const App = (() => {
  let currentUser = null
  let currentUserPromise = null

  const statusLabels = {
    new: 'Novo',
    preparing: 'Em preparo',
    ready: 'Pronto',
    delivered: 'Entregue',
    cancelled: 'Cancelado'
  }

  const statusClasses = {
    new: 'status-new',
    preparing: 'status-preparing',
    ready: 'status-delivery',
    delivered: 'status-done',
    cancelled: 'status-cancelled'
  }

  async function getCurrentUser(force = false) {
    if (!Auth.isLoggedIn()) {
      currentUser = null
      currentUserPromise = null
      return null
    }

    if (currentUser && !force) {
      return currentUser
    }

    if (currentUserPromise && !force) {
      return currentUserPromise
    }

    currentUserPromise = api.get('/users/me')
      .then((response) => {
        currentUser = response.data || null
        return currentUser
      })
      .catch((error) => {
        if (error?.response?.status === 401 || error?.response?.status === 422) {
          logout()
        }
        throw error
      })
      .finally(() => {
        currentUserPromise = null
      })

    return currentUserPromise
  }

  function logout() {
    currentUser = null
    currentUserPromise = null
    Auth.logout()
  }

  function defaultHomeForRole(role) {
    return role === 'owner' ? 'homeowner.html' : 'homeclient.html'
  }

  function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(Number(value || 0))
  }

  function formatDate(value) {
    if (!value) {
      return '-'
    }

    return new Date(value).toLocaleDateString('pt-BR')
  }

  function formatDateTime(value) {
    if (!value) {
      return '-'
    }

    return new Date(value).toLocaleString('pt-BR')
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  function initials(name) {
    return String(name || 'IF')
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join('')
  }

  function statusLabel(status) {
    return statusLabels[status] || status || 'Indefinido'
  }

  function statusClass(status) {
    return statusClasses[status] || 'status-new'
  }

  function groupCartItems(cart) {
    const grouped = new Map()

    cart.forEach((item) => {
      const existing = grouped.get(item.menu_item_id)
      if (existing) {
        existing.quantity += 1
      } else {
        grouped.set(item.menu_item_id, {
          menu_item_id: item.menu_item_id,
          quantity: 1
        })
      }
    })

    return Array.from(grouped.values())
  }

  return {
    defaultHomeForRole,
    escapeHtml,
    formatCurrency,
    formatDate,
    formatDateTime,
    getCurrentUser,
    groupCartItems,
    initials,
    logout,
    statusClass,
    statusLabel
  }
})()
