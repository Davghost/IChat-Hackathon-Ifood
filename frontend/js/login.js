const { createApp, nextTick, onMounted, ref } = Vue

createApp({
  setup() {
    const email = ref('')
    const password = ref('')
    const loginLoading = ref(false)
    const errorMessage = ref('')
    const tokenReceived = ref(false)

    async function login() {
      const trimmedEmail = email.value.trim()

      errorMessage.value = ''
      tokenReceived.value = false

      if (trimmedEmail === '' || password.value === '') {
        errorMessage.value = 'Preencha email e senha.'
        return
      }

      loginLoading.value = true

      try {
        const response = await api.post('/auth/login', {
          email: trimmedEmail,
          password: password.value
        })

        Auth.saveToken(response.data.access_token)
        tokenReceived.value = true
        location.href = '../index.html'
      } catch (error) {
        errorMessage.value = error?.response?.data?.msg || 'Nao foi possivel fazer login.'
        console.error(error)
      } finally {
        loginLoading.value = false
      }
    }

    function refreshIcons() {
      nextTick(() => {
        if (window.lucide) {
          window.lucide.createIcons()
        }
      })
    }

    onMounted(refreshIcons)

    return {
      email,
      password,
      loginLoading,
      errorMessage,
      tokenReceived,
      login
    }
  }
}).mount('#app')
