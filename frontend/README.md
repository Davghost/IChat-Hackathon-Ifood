# iFood Manager Frontend

Frontend estatico em HTML, CSS e Vue 3 via CDN para a experiencia owner.

## Telas

- `pages/login.html`: login JWT.
- `pages/homeowner.html`: dashboard owner.
- `pages/pedidos.html`: fila de pedidos e atualizacao de status.
- `pages/cardapio.html`: CRUD de itens em `/owner/menu-items`.
- `pages/faturamento.html`: historico analitico e previsao derivada.
- `pages/homeclient.html`: placeholder para fluxo de cliente indisponivel na API atual.

## API usada

O arquivo `js/api.js` usa:

```js
const API_URL = 'http://localhost:5000/api'
```

Endpoints integrados:

- `POST /auth/login`
- `GET /owner/dashboard`
- `GET /owner/analytics/history`
- `GET /owner/orders`
- `POST /owner/orders`
- `PATCH /owner/orders/:id/status`
- `GET /owner/menu-items`
- `POST /owner/menu-items`
- `PUT /owner/menu-items/:id`
- `DELETE /owner/menu-items/:id`
- `POST /owner/chat`

## Observacao

O backend atual autentica apenas owners. As rotas antigas de restaurante e cliente nao fazem parte do contrato ativo.
