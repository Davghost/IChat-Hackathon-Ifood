document.addEventListener('DOMContentLoaded', () => {
  const chatButton = document.getElementById('chatButton')
  const chatOverlay = document.getElementById('chatOverlay')
  const chatClose = document.querySelector('.chat-close')
  const chatInput = document.getElementById('chatInput')
  const sendButton = document.getElementById('sendMessage')
  const chatBody = document.getElementById('chatBody')

  if (!chatButton || !chatOverlay || !chatInput || !sendButton || !chatBody) {
    return
  }

  const initialMarkup = chatBody.innerHTML

  chatButton.addEventListener('click', () => {
    chatOverlay.classList.add('active')
  })

  chatClose?.addEventListener('click', closeChat)

  chatOverlay.addEventListener('click', (event) => {
    if (event.target === chatOverlay) {
      closeChat()
    }
  })

  sendButton.addEventListener('click', sendMessage)
  chatInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      sendMessage()
    }
  })

  function closeChat() {
    chatOverlay.classList.remove('active')
    chatBody.innerHTML = initialMarkup
  }

  async function sendMessage() {
    const text = chatInput.value.trim()
    if (!text) {
      return
    }

    appendMessage('user', text)
    chatInput.value = ''
    setPending(true)
    const loadingNode = appendMessage('bot', 'Consultando assistente...')

    try {
      const response = await api.post('/owner/chat', { message: text })
      loadingNode.textContent = normalizeChatReply(response.data?.chatbot_response)
    } catch (error) {
      loadingNode.textContent = error?.response?.data?.msg || 'Nao foi possivel consultar o assistente.'
    } finally {
      setPending(false)
      chatBody.scrollTop = chatBody.scrollHeight
    }
  }

  function appendMessage(role, text) {
    const node = document.createElement('div')
    node.className = `message ${role}`
    node.textContent = text
    chatBody.appendChild(node)
    chatBody.scrollTop = chatBody.scrollHeight
    return node
  }

  function normalizeChatReply(payload) {
    if (typeof payload === 'string') {
      return payload
    }

    if (Array.isArray(payload)) {
      return payload.map(formatReplyEntry).join('\n')
    }

    if (payload && typeof payload === 'object') {
      if (typeof payload.answer === 'string') {
        return payload.answer
      }
      if (typeof payload.response === 'string') {
        return payload.response
      }
      return JSON.stringify(payload, null, 2)
    }

    return 'Assistente respondeu sem conteudo.'
  }

  function formatReplyEntry(entry) {
    if (typeof entry === 'string') {
      return entry
    }
    return JSON.stringify(entry)
  }

  function setPending(isPending) {
    chatInput.disabled = isPending
    sendButton.disabled = isPending
  }
})
