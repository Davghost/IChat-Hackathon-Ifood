# iChat iFood Hackathon

Esse repositório contém um projeto full-stack criado para hackathons, com backend em Flask, frontend estático em HTML/CSS/JavaScript e notebooks de experimentação de IA para previsão.

## Visão Geral

O projeto simula uma plataforma de gestão para donos de restaurantes.

Principais componentes:
- `backend/`: API REST em Flask com autenticação JWT, CRUD de cardápio, controle de pedidos, painel analítico e integração com chatbot.
- `frontend/`: interface estática para donos de restaurante acessarem login, dashboard, cardápio, pedidos e faturamento.
- `datasets/`: conjuntos de dados usados para popular a base e gerar métricas reais.
- `IA models/`: notebooks de análise e modelos para previsão de demanda e entrega.

---

## Funcionalidades

### Backend

- Autenticação JWT via `/api/auth/login`
- Login exclusivo para usuários com papel `owner`
- CRUD de itens do cardápio (`/api/owner/menu-items`)
- Consulta de pedidos com filtros e paginação (`/api/owner/orders`)
- Atualização de status de pedido (`/api/owner/orders/:id/status`)
- Dashboard de performance do restaurante (`/api/owner/dashboard`)
- Histórico analítico filtrável por período, bairro e prato (`/api/owner/analytics/history`)
- Chat via webhook para assistente externo (`/api/owner/chat`)
- Documentação de API gerada pelo Spectree em `/docs`

### Frontend

- Login com JWT e armazenamento de token em `localStorage`
- Dashboard com métricas de pedidos, receita e itens mais vendidos
- Página de gerenciamento de cardápio (novo, editar, remover itens)
- Página de pedidos com contagem por status e atualização de status em tempo real
- Área de faturamento/analytics com gráficos e histórico
- UI leve em HTML/CSS/JS + Vue 3 via CDN

### Dados e IA

- `datasets/deliveries_train.csv`: pedidos e entregas históricas
- `datasets/demand_daily_train.csv`: demanda diária, receita e indicadores temporais
- `IA models/PrevisãoDeDemanda.ipynb`: notebook para análise e previsão de demanda
- `IA models/PrevisãoDeEntrega.ipynb`: notebook para análise e previsão de tempo de entrega

---

## Arquitetura

### Backend

O backend usa:
- Flask 3
- Flask SQLAlchemy
- Flask-Migrate
- Flask-JWT-Extended
- Spectree para validação e documentação
- SQLite como banco local

Modelos principais:
- `User`: usuário do sistema, com papel `owner`
- `MenuItem`: itens do cardápio vinculados ao owner
- `TrainRecord`: base de registros de pedidos, usada para alimentar dashboards e filtros

O backend mantém um contrato de API simples e separado por blueprint:
- `auth_controller.py`
- `chat_controller.py`
- `controllers/owner/menu_items_controller.py`
- `controllers/owner/orders_controller.py`
- `controllers/owner/analytics_controller.py`

### Frontend

O frontend é hospedado como arquivos estáticos em `frontend/`.
Ele usa:
- `axios` para chamadas à API
- `Vue 3` via CDN para a tela de login
- Código utilitário em `frontend/js/app-utils.js`
- Controle de sessão no browser por `frontend/js/auth.js`

Páginas estáticas:
- `frontend/pages/login.html`
- `frontend/pages/homeowner.html`
- `frontend/pages/pedidos.html`
- `frontend/pages/cardapio.html`
- `frontend/pages/faturamento.html`
- `frontend/pages/homeclient.html` (placeholder de cliente)

---

## Dependências

O backend depende de pacotes definidos em `backend/requirements.txt`:
- Flask
- Flask-CORS
- Flask-JWT-Extended
- Flask-Migrate
- Flask-SQLAlchemy
- Spectree
- python-dotenv
- pydantic
- supabase

> O frontend não requer build: basta abrir os arquivos estáticos ou servir a pasta `frontend/` com um servidor HTTP.

---

## Como rodar

### 1. Configurar ambiente Python

No diretório `backend/`:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

O backend usa:
- `SECRET_KEY`
- `JWT_SECRET_KEY`

Você pode criar um arquivo `.env` em `backend/` com:

```env
SECRET_KEY=uma_chave_secreta_aqui
JWT_SECRET_KEY=uma_chave_jwt_secreta_aqui
```

### 3. Popular o banco de dados

Execute:

```bash
python populate_database.py
```

Isso cria ou atualiza o usuário owner padrão e importa dados dos CSVs em `datasets/`.

Credenciais padrão:
- email: `owner@hackathon.local`
- senha: `owner123`

### 4. Iniciar o backend

Ainda em `backend/`:

```bash
python main.py
```

O servidor iniciará em `http://localhost:5000`.

### 5. Abrir o frontend

A forma mais confiável é servir os arquivos estáticos com um servidor HTTP, por exemplo:

```bash
cd frontend
python3 -m http.server 8000
```

Então abra no navegador:
- `http://localhost:8000/pages/login.html`

> Também é possível abrir os arquivos diretamente, mas alguns recursos de browser podem exigir servidor HTTP.

---

## Rotas principais da API

### Autenticação

- `POST /api/auth/login`
  - Corpo: `{ "email": string, "password": string }`
  - Retorno: `{ "access_token": string }`

### Owner

- `GET /api/owner/dashboard`
- `GET /api/owner/analytics/history`
- `GET /api/owner/orders`
- `POST /api/owner/orders`
- `PATCH /api/owner/orders/:id/status`
- `GET /api/owner/menu-items`
- `POST /api/owner/menu-items`
- `PUT /api/owner/menu-items/:id`
- `DELETE /api/owner/menu-items/:id`
- `POST /api/owner/chat`

### Documentação

- `GET /docs`

---

## Pontos importantes

- A autenticação é feita apenas para usuário com papel `owner`.
- O backend usa `TrainRecord` para unificar dados históricos importados dos datasets e pedidos criados no aplicativo.
- O endpoint `/owner/chat` encaminha mensagens para um webhook externo.
- Não há endpoint de cadastro de usuário no fluxo atual; use `populate_database.py` para criar o usuário owner.
- O frontend está preparado para uso owner e oferece acesso apenas após login.

---

## Dados e IA

Os dados de treino estão em:
- `datasets/deliveries_train.csv`
- `datasets/demand_daily_train.csv`

Notebooks de análise:
- `IA models/PrevisãoDeDemanda.ipynb`
- `IA models/PrevisãoDeEntrega.ipynb`

Esses notebooks são voltados a provas de conceito e previsão de demanda/entrega, e podem ser usados para evoluir o sistema com modelos de machine learning.

---

## Possíveis melhorias

- Adicionar registro e recuperação de senha
- Tratar múltiplas contas e restaurantes por owner
- Integrar modelo de previsão diretamente ao backend
- Melhorar a interface de cliente para pedidos e checkout
- Migrar para PostgreSQL ou outro banco de produção
- Refinar controle de permissões e testes automatizados

---

## Observações finais

Esse projeto combina dados reais de entrega com um backend funcional e interface web simples. Ele já oferece um MVP completo para gestão de restaurante e fornece base para evolução em IA, UX e operações.
