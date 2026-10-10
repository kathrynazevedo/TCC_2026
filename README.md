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
├── package.json              # scripts da raiz (install:all, dev, dev:api, dev:web, build, start, test)
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
    ├── deteccao.py           # regras: classes, monta pessoas (cabeça + tronco), um alerta por pessoa e infração
    ├── rastreador.py         # rastreamento por centroide: ID estável por pessoa entre frames
    ├── cliente_api.py        # envio à API, heartbeat e fila offline (reenvio automático)
    ├── teste_conexao.py      # diagnóstico de rede/chave (--infracao envia uma infração de teste)
    ├── best.tflite           # modelo treinado
    ├── requirements.txt      # dependências Python
    ├── setup.sh              # prepara a Raspberry (venv, dependências e .env)
    └── .env.example          # modelo das variáveis de ambiente
```

---

## 🚀 Como executar

Pré-requisitos: **Node.js 20+**, um banco **PostgreSQL** (o projeto usa o [Neon](https://neon.tech)) e uma conta no **Cloudinary**.

### 1. Banco de dados

Execute no banco, nesta ordem: `backend_api/db/schema.sql` e, para ter dados de demonstração, `backend_api/db/seed.sql` (cria 3 zonas, a câmera `RPI-TCC-001` com `id_dispositivo = 1` e alguns trabalhadores).

> **Banco já existente?** Rode o `schema.sql` de novo antes de publicar a API nova: ele é idempotente e cria a tabela `ocorrencia` e as colunas `infracao.id_ocorrencia` / `infracao.numero_pessoa`. Os registros antigos continuam como estão.

### 2. Backend

```bash
npm run install:all
cp backend_api/.env.example backend_api/.env   # preencha DATABASE_URL, CLOUDINARY_* e EDGE_API_KEY
```

No Windows (CMD), use `copy backend_api\.env.example backend_api\.env`.

### 3. Subir tudo (desenvolvimento)

```bash
npm run dev     # API em http://localhost:3000 + dashboard em http://localhost:5173
```

Um único terminal roda os dois servidores (logs prefixados com `[api]` e `[web]`); `Ctrl+C` encerra ambos.
Para subir só um deles: `npm run dev:api` ou `npm run dev:web`.

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

Para provar também o envio de uma infração com foto (sem câmera nem modelo), rode `teste_conexao.py --infracao`. A infração de teste fica no banco; o script mostra o comando SQL para apagá-la.

Se a API estiver fora do ar, os alertas ficam em `pendentes/` e são reenviados automaticamente a cada minuto.

---

## 🔌 API

| Método | Rota | Quem usa | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | todos | Estado da API e do banco |
| `POST` | `/api/occurrences` | Raspberry 🔑 | **Registra a cena inteira de uma captura** (`multipart`: `image` + `occurrence`, um JSON — ver abaixo) |
| `POST` | `/api/violations` | Raspberry 🔑 | Registra uma infração isolada (formato antigo, mantido por compatibilidade; `multipart`: `image`, `id_dispositivo`, `tipo_epi_ausente`, `confidence`, `timestamp`, `severity`) |
| `GET` | `/api/violations?limit=&status=` | dashboard | Lista infrações (mais recentes primeiro, máx. 1000). Cada uma traz também `occurrence_id`, `person_number`, `people_total` e `people` (a cena) |
| `PATCH` | `/api/violations/:id` | dashboard | Altera status: `active` → `acknowledged` → `resolved` |
| `DELETE` | `/api/violations` | dashboard 🔒 | Exclui em lote do banco e do Cloudinary: `{ "ids": [1, 2], "password": "..." }`. Senha em `DELETE_PASSWORD` (padrão `12345`); errada → `403` |
| `GET` | `/api/metrics` | dashboard | Totais, não conformidades, taxa de segurança, câmeras |
| `GET` | `/api/areas` | dashboard | Zonas com seus dispositivos e se estão online |
| `GET` | `/api/workers` | dashboard | Equipe cadastrada |
| `POST` | `/api/status/heartbeat` | Raspberry 🔑 | Sinal de vida da placa |
| `GET` | `/api/status/edge` | dashboard | Placa online/offline |

🔑 exige o header `x-api-key` com o valor de `EDGE_API_KEY`.

Códigos de tipo de EPI: `no-helmet` (sem capacete), `no-vest` (sem colete) e `no-helmet-no-vest` (sem capacete **e** sem colete). Quando a **mesma pessoa** está sem capacete e sem colete na mesma captura, a API grava **um único** registro `no-helmet-no-vest`, em vez de dois. Duas pessoas diferentes (uma sem capacete, outra sem colete) continuam em registros separados.

### Ocorrência: a cena inteira numa única requisição

Em vez de uma requisição por infração (cada uma repetindo a mesma foto), a placa envia **uma ocorrência** por captura: a foto uma vez e um JSON com todas as pessoas do frame, com ou sem EPI.

```json
{
  "id_dispositivo": 1,
  "timestamp": "2026-10-10T20:13:36+00:00",
  "severity": "high",
  "total_pessoas": 2,
  "pessoas": [
    { "numero": 1, "caixa": [140, 39, 400, 479],
      "capacete": { "estado": "ok",      "confianca": 0.91, "novo": false },
      "colete":   { "estado": "ausente", "confianca": 0.83, "novo": true } },
    { "numero": 2, "caixa": [154, 174, 640, 479],
      "capacete": { "estado": "ausente", "confianca": 0.87, "novo": true },
      "colete":   { "estado": "ausente", "confianca": 0.78, "novo": true } }
  ]
}
```

- `numero`: posição da pessoa por ordem de chegada entre quem está em cena (a mesma numeração desenhada na foto).
- `estado`: `ok`, `ausente` ou `desconhecido` (a parte do corpo não foi detectada; nunca vira infração).
- `novo`: `true` só no que disparou um alerta agora. É isso que a API grava em `infracao` (uma linha por pessoa e EPI novo, com `id_ocorrencia` e `numero_pessoa`; capacete + colete novos da mesma pessoa viram uma linha `no-helmet-no-vest`); o restante fica na cena como contexto.
- A ocorrência e suas infrações são gravadas numa **transação**: ou entra tudo, ou nada (a foto órfã é removida do Cloudinary).
- `total_pessoas` é a contagem em cena (pode incluir quem acabou de sair do enquadramento) e nunca é menor que a lista `pessoas`.

## ⚙️ Variáveis de ambiente

Veja os modelos `backend_api/.env.example`, `frontend/.env.example` e `raspberry/tcc_producao/.env.example` — todos comentados.

## ✅ Testes

```bash
npm test                                                  # API: 33 testes de integração
(cd raspberry/tcc_producao && python -m unittest discover -s tests)   # placa: 40 testes (sem câmera nem modelo)
npm run lint                                              # frontend
```

Os testes da API usam um PostgreSQL em memória e um Cloudinary simulado: não precisam de `.env`, internet nem do banco real.

## 📝 Observações e limitações conhecidas

- **Autenticação do dashboard é simulada** (usuário fixo em `frontend/src/lib/AuthContext.jsx`). A proteção existe apenas nas rotas da placa. Para uso real, adicione login antes de expor o painel na internet.
- **Taxa de segurança** = ocorrências que não estão pendentes (`active`) ÷ total. Ocorrências "reconhecidas" contam como tratadas.
- O histórico do Git ainda contém a senha de teste da câmera (`admin:admin123`) e fotos de infrações de versões antigas. **Troque a senha do DVR/câmera**; se o repositório for público, considere limpar o histórico.
- O modelo `.tflite` espera as classes `Sem_Capacete` / `Sem_Colete` (ou `no-helmet` / `no-vest`); outros nomes são ignorados — ajuste em `deteccao.py` se retreinar o modelo.
