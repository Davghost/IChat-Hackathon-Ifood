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
- `GET /owner/restaurant`
- `POST /owner/restaurant`
- `PUT /owner/restaurant`
- `DELETE /owner/restaurant`
- `GET /owner/menus`
- `POST /owner/menus`
- `PUT /owner/menus/:id`
- `DELETE /owner/menus/:id`

## Observacao

O fluxo do owner foi simplificado para um restaurante unico por usuario owner. O cardapio do owner sempre fica vinculado a essa unica unidade.
