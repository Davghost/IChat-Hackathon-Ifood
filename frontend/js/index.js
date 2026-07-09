const { computed, createApp, nextTick, onMounted, ref, watch } = Vue

const statusMap = [
  { label: 'Novo', className: 'status-new' },
  { label: 'Preparando', className: 'status-preparing' },
  { label: 'Saiu para entrega', className: 'status-delivery' },
  { label: 'Entregue', className: 'status-done' }
]

const customerNames = [
  'Ana Costa',
  'Bruno Lima',
  'Camila Rocha',
  'Diego Alves',
  'Fernanda Melo',
  'Gabriel Souza',
  'Helena Castro',
  'Igor Martins'
]

createApp({
  setup() {
    const activeView = ref('overview')
    const isLoggedIn = ref(Auth.isLoggedIn())
    const loading = ref(isLoggedIn.value)
    const saving = ref(false)
    const errorMessage = ref('')
    const successMessage = ref('')
    const user = ref(null)
    const restaurants = ref([])
    const menuItems = ref([])

    const restaurantForm = ref(emptyRestaurantForm())
    const menuForm = ref(emptyMenuForm())

    const userEmail = computed(() => user.value?.email || '')

    const formattedToday = computed(() => {
      return new Intl.DateTimeFormat('pt-BR', {
        weekday: 'long',
        day: '2-digit',
        month: 'long'
      }).format(new Date())
    })

    const todayOrders = computed(() => {
      const sourceItems = menuItems.value.length
        ? menuItems.value
        : [
            {
              id: 1,
              name: 'Combo especial',
              price: 42.9,
              restaurant_id: restaurants.value[0]?.id || null
            },
            {
              id: 2,
              name: 'Prato executivo',
              price: 34.5,
              restaurant_id: restaurants.value[0]?.id || null
            }
          ]

      return Array.from({ length: Math.min(Math.max(sourceItems.length * 2, 4), 10) }, (_, index) => {
        const item = sourceItems[index % sourceItems.length]
        const status = statusMap[index % statusMap.length]
        const quantity = (index % 3) + 1

        return {
          id: 1200 + index + 1,
          customer: customerNames[index % customerNames.length],
          itemName: item.name,
          quantity,
          status: status.label,
          statusClass: status.className,
          time: `${String(11 + (index % 9)).padStart(2, '0')}:${String((index * 7) % 60).padStart(2, '0')}`,
          total: Number(item.price || 0) * quantity
        }
      })
    })

    const dashboard = computed(() => {
      const orders = todayOrders.value
      const revenueToday = orders.reduce((sum, order) => sum + order.total, 0)
      const pendingOrders = orders.filter((order) => order.status !== 'Entregue').length
      const deliveredOrders = orders.length - pendingOrders
      const itemsSold = orders.reduce((sum, order) => sum + order.quantity, 0)

      return {
        ordersToday: orders.length,
        revenueToday,
        pendingOrders,
        deliveredOrders,
        itemsSold,
        averageTicket: orders.length ? revenueToday / orders.length : 0,
        rating: restaurants.value.length ? '4.8' : '4.7',
        deliveryTime: Math.max(24, 42 - menuItems.value.length)
      }
    })

    const topMenuItems = computed(() => {
      return [...menuItems.value]
        .sort((a, b) => Number(b.price) - Number(a.price))
        .slice(0, 5)
        .map((item, index) => ({
          ...item,
          rank: String(index + 1).padStart(2, '0')
        }))
    })

    const revenueBars = computed(() => {
      const labels = ['10h', '12h', '14h', '16h', '18h', '20h']
      const base = Math.max(dashboard.value.revenueToday, 1)

      return labels.map((label, index) => {
        const slice = todayOrders.value
          .filter((_, orderIndex) => orderIndex % labels.length <= index)
          .reduce((sum, order) => sum + order.total, 0)

        return {
          label,
          height: Math.max(18, Math.round((slice / base) * 82))
        }
      })
    })

    async function loadDashboard() {
      if (!isLoggedIn.value) {
        loading.value = false
        return
      }

      loading.value = true
      errorMessage.value = ''

      try {
        const [currentUser, ordersResponse] = await Promise.all([
          App.getCurrentUser(true),
          api.get('/owner/orders?page=1&per_page=10&days=7')
        ])

        user.value = currentUser
        restaurants.value = []
        menuItems.value = (ordersResponse.data?.orders || []).map((order) => ({
          id: order.id,
          name: order.main_dish,
          price: order.total_price,
          restaurant_id: null
        }))
        showSuccess('Painel sincronizado com as rotas atuais do backend.')
      } catch (error) {
        handleRequestError(error, 'Nao foi possivel carregar o painel.')
      } finally {
        loading.value = false
        refreshIcons()
      }
    }

    async function saveRestaurant() {
      saving.value = true
      clearMessages()

      try {
        throw new Error('disabled-route')
      } catch (error) {
        errorMessage.value = 'A API atual nao possui mais CRUD de restaurante.'
      } finally {
        saving.value = false
        refreshIcons()
      }
    }

    async function deleteRestaurant(id) {
      if (!confirm('Excluir esta loja? Os itens vinculados tambem podem ser removidos pelo backend.')) {
        return
      }

      clearMessages()

      try {
        throw new Error('disabled-route')
      } catch (error) {
        errorMessage.value = 'A API atual nao possui mais CRUD de restaurante.'
      }
    }

    async function saveMenuItem() {
      saving.value = true
      clearMessages()

      try {
        throw new Error('disabled-route')
      } catch (error) {
        errorMessage.value = 'A API atual nao possui mais CRUD de cardapio.'
      } finally {
        saving.value = false
        refreshIcons()
      }
    }

    async function deleteMenuItem(id) {
      if (!confirm('Excluir este item do cardapio?')) {
        return
      }

      clearMessages()

      try {
        throw new Error('disabled-route')
      } catch (error) {
        errorMessage.value = 'A API atual nao possui mais CRUD de cardapio.'
      }
    }

    function editRestaurant(restaurant) {
      restaurantForm.value = { ...restaurant }
      activeView.value = 'restaurants'
      refreshIcons()
    }

    function editMenuItem(item) {
      menuForm.value = {
        id: item.id,
        title: item.title,
        name: item.name,
        price: item.price,
        description: item.description,
        restaurant_id: item.restaurant_id
      }
      activeView.value = 'menu'
      refreshIcons()
    }

    function openMenuCreate() {
      resetMenuForm()
      activeView.value = 'menu'
      refreshIcons()
    }

    function resetRestaurantForm() {
      restaurantForm.value = emptyRestaurantForm()
    }

    function resetMenuForm() {
      menuForm.value = emptyMenuForm()
    }

    function restaurantName(id) {
      const restaurant = restaurants.value.find((item) => item.id === id)
      return restaurant?.name || 'Nao vinculada'
    }

    function restaurantItemCount(id) {
      return menuItems.value.filter((item) => item.restaurant_id === id).length
    }

    function initials(name) {
      return String(name || 'Loja')
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0].toUpperCase())
        .join('')
    }

    function formatCurrency(value) {
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
      }).format(Number(value || 0))
    }

    function logout() {
      Auth.logout()
      isLoggedIn.value = false
      user.value = null
      restaurants.value = []
      menuItems.value = []
      location.href = 'pages/login.html'
    }

    function clearMessages() {
      errorMessage.value = ''
      successMessage.value = ''
    }

    function showSuccess(message) {
      successMessage.value = message
      window.setTimeout(() => {
        if (successMessage.value === message) {
          successMessage.value = ''
        }
      }, 2400)
    }

    function handleRequestError(error, fallbackMessage) {
      if (error?.response?.status === 401 || error?.response?.status === 422) {
        Auth.logout()
        isLoggedIn.value = false
        errorMessage.value = 'Sua sessao expirou. Entre novamente.'
        return
      }

      errorMessage.value = error?.response?.data?.msg || fallbackMessage
      console.error(error)
    }

    function refreshIcons() {
      nextTick(() => {
        if (window.lucide) {
          window.lucide.createIcons()
        }
      })
    }

    watch(activeView, refreshIcons)

    onMounted(() => {
      loadDashboard()
      refreshIcons()
    })

    return {
      activeView,
      dashboard,
      deleteMenuItem,
      deleteRestaurant,
      editMenuItem,
      editRestaurant,
      errorMessage,
      formatCurrency,
      formattedToday,
      initials,
      isLoggedIn,
      loading,
      logout,
      menuForm,
      menuItems,
      openMenuCreate,
      resetMenuForm,
      resetRestaurantForm,
      restaurantForm,
      restaurantItemCount,
      restaurantName,
      restaurants,
      revenueBars,
      saveMenuItem,
      saveRestaurant,
      saving,
      successMessage,
      todayOrders,
      topMenuItems,
      userEmail
    }
  }
}).mount('#app')

function emptyRestaurantForm() {
  return {
    id: null,
    name: '',
    description: ''
  }
}

function emptyMenuForm() {
  return {
    id: null,
    title: '',
    name: '',
    price: '',
    description: '',
    restaurant_id: null
  }
}

function normalizeRestaurantId(value) {
  if (value === '' || value === null || value === undefined) {
    return null
  }

  return Number(value)
}
