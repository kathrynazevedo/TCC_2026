<h1 align="center">
  🏗️ Sistema Inteligente de Detecção de EPIs em Obras Civis
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/YOLOv8-FF0000?style=for-the-badge&logo=ultralytics&logoColor=white" alt="YOLOv8" />
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

> **Trabalho de Conclusão de Curso (TCC)** em Ciência da Computação pela Universidade Paulista (UNIP).

Sistema de câmera inteligente baseado em Visão Computacional que monitora canteiros de obras e identifica, em tempo real, trabalhadores sem os Equipamentos de Proteção Individual (EPIs) obrigatórios — **capacete** e **colete**. A detecção roda na borda (Raspberry Pi), aciona uma sirene local e envia a evidência para a nuvem, onde um painel web acompanha as ocorrências.

---

## 🧩 Arquitetura

```text
┌──────────────────────┐   POST /api/violations (foto + dados)    ┌─────────────────────────┐
│  Raspberry Pi        │ ───────────────────────────────────────▶ │  Backend Node.js        │
│  câmera → YOLO       │   POST /api/status/heartbeat (30 s)      │  Express 5              │
│  sirene (GPIO)       │                                          │  ├─ PostgreSQL (Neon)   │
│  fila offline        │                                          │  ├─ Cloudinary (fotos)  │
└──────────────────────┘                                          │  └─ serve o React (dist)│
                                                                  └────────────┬────────────┘
                                                                               │ GET /api/*
                                                                  ┌────────────▼────────────┐
                                                                  │  Dashboard React        │
                                                                  │  (atualiza a cada 5 s)  │
                                                                  └─────────────────────────┘
```

É um **monorepo/monolito** com três partes independentes no mesmo repositório. Em produção o próprio backend entrega o dashboard compilado, então basta um único servidor.

| Camada | Pasta | Tecnologias |
| :--- | :--- | :--- |
| **Borda (IA)** | `raspberry/tcc_producao` | Python, YOLOv8 (Ultralytics, modelo `.tflite`), OpenCV, RPi.GPIO |
| **Backend / API** | `backend_api` | Node.js, Express 5, PostgreSQL (Neon), Cloudinary, Multer |
| **Dashboard** | `frontend` | React 18, Vite, Tailwind CSS, shadcn/ui, TanStack Query, Recharts |

## 📂 Estrutura

```text
.
├── package.json              # scripts da raiz (install:all, dev:api, dev:web, build, start, test)
├── backend_api/
│   ├── server.js             # inicializa o servidor (porta, encerramento limpo)
│   ├── src/
│   │   ├── app.js            # monta o Express (CORS, rotas, erros, serve o front)
│   │   ├── config/           # env, banco (pg), cloudinary
│   │   ├── routes/           # rotas finas
│   │   ├── controllers/      # regras de cada endpoint
│   │   ├── middlewares/      # autenticação da placa, upload, tratamento de erros
│   │   ├── services/         # armazenamento das imagens (Cloudinary)
│   │   └── utils/            # validações e HttpError
│   ├── db/                   # schema.sql e seed.sql
│   └── tests/                # testes de integração (node:test + pg-mem)
├── frontend/
│   └── src/
│       ├── api/              # apiClient.js + hooks do React Query
│       ├── pages/            # Dashboard, Violações, Zonas, Equipe, Relatórios, Sistema
│       ├── components/       # layout, dashboard, common e ui (shadcn)
│       └── lib/              # formatação, rótulos, geração de relatórios (PDF/CSV/ZIP)
└── raspberry/tcc_producao/
    ├── main.py               # loop principal: câmera → modelo → sirene + alerta
    ├── config.py             # configurações (variáveis de ambiente / .env)
    ├── deteccao.py           # regras: classes, confiança mínima, debounce
    ├── cliente_api.py        # envio à API, heartbeat e fila offline
    ├── sincronizar.py        # reenvio manual dos alertas pendentes
    ├── teste_conexao.py      # diagnóstico de rede/chave de API
    ├── best.tflite           # modelo treinado
    └── tests/                # testes unitários da borda
```

---

## 🚀 Como executar

Pré-requisitos: **Node.js 20+**, um banco **PostgreSQL** (o projeto usa o [Neon](https://neon.tech)) e uma conta no **Cloudinary**.

### 1. Banco de dados

Execute no banco, nesta ordem: `backend_api/db/schema.sql` e, para ter dados de demonstração, `backend_api/db/seed.sql` (cria 3 zonas, a câmera `RPI-TCC-001` com `id_dispositivo = 1` e alguns trabalhadores).

### 2. Backend

```bash
npm run install:all
cp backend_api/.env.example backend_api/.env   # preencha DATABASE_URL, CLOUDINARY_* e EDGE_API_KEY
npm run dev:api                                # http://localhost:3000
```

### 3. Dashboard (desenvolvimento)

```bash
npm run dev:web                                # http://localhost:5173
```

O Vite repassa `/api` para `localhost:3000`, então não há configuração extra nem problema de CORS.

### 4. Produção (um único servidor)

```bash
npm run build      # gera frontend/dist
npm start          # o backend serve a API e o dashboard em http://localhost:3000
```

Em produção defina `NODE_ENV=production` (exige `EDGE_API_KEY` e recomenda `CORS_ORIGIN`).

### 5. Raspberry Pi

```bash
cd raspberry/tcc_producao
./setup.sh                          # cria o .venv, instala as dependências e gera o .env
nano .env                           # API_BASE_URL, EDGE_API_KEY (a mesma do backend), CAMERA_SOURCE...
.venv/bin/python teste_conexao.py   # confere rede, API e chave
.venv/bin/python main.py
```

Se a API estiver fora do ar, os alertas ficam em `pendentes/` e são reenviados automaticamente a cada minuto (ou manualmente com `sincronizar.py`).

---

## 🔌 API

| Método | Rota | Quem usa | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | todos | Estado da API e do banco |
| `POST` | `/api/violations` | Raspberry 🔑 | Registra infração (`multipart`: `image`, `id_dispositivo`, `tipo_epi_ausente`, `confidence`, `timestamp`, `severity`) |
| `GET` | `/api/violations?limit=&status=` | dashboard | Lista infrações (mais recentes primeiro, máx. 1000) |
| `PATCH` | `/api/violations/:id` | dashboard | Altera status: `active` → `acknowledged` → `resolved` |
| `GET` | `/api/metrics` | dashboard | Totais, não conformidades, taxa de segurança, câmeras |
| `GET` | `/api/areas` | dashboard | Zonas com seus dispositivos e se estão online |
| `GET` | `/api/workers` | dashboard | Equipe cadastrada |
| `POST` | `/api/status/heartbeat` | Raspberry 🔑 | Sinal de vida da placa |
| `GET` | `/api/status/edge` | dashboard | Placa online/offline |

🔑 exige o header `x-api-key` com o valor de `EDGE_API_KEY`.

Códigos de tipo de EPI: `no-helmet` (sem capacete) e `no-vest` (sem colete).

## ⚙️ Variáveis de ambiente

Veja os modelos `backend_api/.env.example`, `frontend/.env.example` e `raspberry/tcc_producao/.env.example` — todos comentados.

## ✅ Testes

```bash
npm test                                                  # API: 20 testes de integração
npm run lint                                              # frontend
cd raspberry/tcc_producao && python -m unittest discover -s tests -v   # borda
```

Os testes da API usam um PostgreSQL em memória e um Cloudinary simulado: não precisam de `.env`, internet nem do banco real.

## 📝 Observações e limitações conhecidas

- **Autenticação do dashboard é simulada** (usuário fixo em `frontend/src/lib/AuthContext.jsx`). A proteção existe apenas nas rotas da placa. Para uso real, adicione login antes de expor o painel na internet.
- **Taxa de segurança** = ocorrências que não estão pendentes (`active`) ÷ total. Ocorrências "reconhecidas" contam como tratadas.
- O histórico do Git ainda contém a senha de teste da câmera (`admin:admin123`) e fotos de infrações de versões antigas. **Troque a senha do DVR/câmera**; se o repositório for público, considere limpar o histórico.
- O modelo `.tflite` espera as classes `Sem_Capacete` / `Sem_Colete` (ou `no-helmet` / `no-vest`); outros nomes são ignorados — ajuste em `deteccao.py` se retreinar o modelo.
