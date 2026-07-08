# iFood Manager Frontend

Frontend estatico em HTML, CSS e Vue 3 via CDN para donos de restaurante.

## Telas

- `index.html`: dashboard com resumo do dia, pedidos demonstrativos, CRUD de lojas, CRUD de cardapio e faturamento.
- `pages/login.html`: login JWT.

## API usada

O arquivo `js/api.js` usa:

```js
const API_URL = 'http://localhost:5000/api'
```

Endpoints integrados:

- `POST /auth/login`
- `GET /users/me`
- `GET /owner/restaurants`
- `POST /owner/restaurants`
- `PUT /owner/restaurants/:id`
- `DELETE /owner/restaurants/:id`
- `GET /owner/menus`
- `POST /owner/menus`
- `PUT /owner/menus/:id`
- `DELETE /owner/menus/:id`

## Observacao

O backend atual nao possui models/controllers de pedidos ou faturamento. Por isso, as secoes de pedidos do dia e faturamento usam uma projecao local baseada nos itens do cardapio carregados da API.
