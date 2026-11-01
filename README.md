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
    ├── main.py               # laço principal: câmera → modelo → regras → sirene + alerta + métricas
    ├── config.py             # configurações (variáveis de ambiente / .env)
    ├── deteccao.py           # regras: acha o EPI dentro da caixa de cada pessoa; falta contínua = um alerta por pessoa e infração
    ├── rastreador.py         # rastreamento por centroide: ID estável por pessoa entre frames
    ├── cliente_api.py        # envio à API, heartbeat (com telemetria) e fila offline (reenvio automático)
    ├── sirene.py             # relé da sirene no GPIO (pino físico, nível configurável); simulada fora da Raspberry
    ├── metricas.py           # métricas, telemetria, confiança por classe, carga de cena, registro de reinícios e CSV
    ├── reinicio.py           # reinício programado do turno (programa ou placa)
    ├── teste_conexao.py      # diagnóstico de rede/chave (--infracao envia uma ocorrência de teste)
    ├── testar_sirene.py      # teste de bancada do relé
    ├── testar_modelo.py      # confere um modelo (--so-classes) ou o roda na câmera/vídeo com a regra do sistema
    ├── modelo_pessoa_epi.tflite   # modelo treinado (3 classes: capacete, colete, pessoa)
    ├── validacao_modelo.json # mAP por classe do modelo, mostrado na tela Sistema
    ├── tests/                # testes da placa (sem câmera, modelo nem GPIO)
    ├── requirements.txt      # dependências Python
    ├── setup.sh              # prepara a Raspberry do zero (venv, dependências e .env)
    ├── instalar_servico.sh   # instala o serviço systemd (sobe ao ligar a placa, volta se cair)
    ├── tcc-epi.service.modelo # modelo do serviço, preenchido pelo instalar_servico.sh
    └── .env.example          # modelo das variáveis de ambiente
```

---

## 🚀 Como executar

Pré-requisitos: **Node.js 20+**, um banco **PostgreSQL** (o projeto usa o [Neon](https://neon.tech)) e uma conta no **Cloudinary**.

### 1. Banco de dados

Execute no banco, nesta ordem: `backend_api/db/schema.sql` e, para ter dados de demonstração, `backend_api/db/seed.sql` (cria 3 zonas, a câmera `RPI-TCC-001` com `id_dispositivo = 1` e alguns trabalhadores).

> **Banco com o ENUM `tipo_epi`?** (é o caso do Neon deste projeto) Rode também `backend_api/db/migracao_tipo_epi.sql`, que acrescenta o valor `no-helmet-no-vest`. Sem ele, a mesma pessoa sem capacete **e** sem colete dá erro 500 na API. O banco ainda exige `score_confianca >= 0.5`, então não abaixe `CONFIANCA_PESSOA` da placa de 0,50.

> **Banco já existente?** Rode o `schema.sql` de novo antes de publicar a API nova: ele é idempotente e cria a tabela `ocorrencia`, as colunas `infracao.id_ocorrencia` / `infracao.numero_pessoa` e as colunas de telemetria `dispositivo_borda.telemetria` / `telemetria_em`. Os registros antigos continuam como estão. Sem as colunas de telemetria a API segue funcionando (a placa continua "online"); só a tela Sistema fica sem os cartões.

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

**Primeira instalação** (placa nova):

```bash
cd raspberry/tcc_producao
bash setup.sh                       # cria o .venv, instala as dependências e gera o .env
nano .env                           # API_BASE_URL, EDGE_API_KEY (a mesma do backend), CAMERA_SOURCE...
.venv/bin/python teste_conexao.py   # confere rede, API e chave
.venv/bin/python testar_sirene.py   # confere o relé de ouvido
bash instalar_servico.sh            # o programa passa a subir sozinho ao ligar a placa
```

Se a placa já tem as dependências no Python do sistema (é o caso da placa do projeto), pule o `setup.sh` e use `python3` no lugar de `.venv/bin/python`; o `instalar_servico.sh` escolhe o Python certo sozinho.

**Como serviço** (`instalar_servico.sh`, usa o `systemd`): o programa sobe ao ligar a placa e volta em 5 s se cair. Se o problema for de configuração (modelo ausente ou sem as 3 classes, saída 2), ele **não** fica reiniciando em laço.

```bash
journalctl -u tcc-epi -f            # o que o programa escreve (alertas, métricas, erros)
sudo systemctl stop tcc-epi         # para antes de testar na mão: libera a câmera e a sirene
sudo systemctl start tcc-epi
bash instalar_servico.sh --remover  # desinstala o serviço
```

**Ferramentas** (rodam na placa ou no PC; nenhuma altera o sistema em operação):

| Arquivo | Para quê |
|---|---|
| `teste_conexao.py` | Confere rede, chave e heartbeat. Com `--infracao` envia uma ocorrência de teste (uma pessoa sem capacete **e** sem colete, com foto) e mostra o SQL para apagá-la do banco. |
| `testar_sirene.py` | Teste de bancada do relé: repouso → sirene → repouso, com o pino e o nível do `.env`. |
| `testar_modelo.py` | `--so-classes` confere se um modelo serve ao sistema; sem opções roda o modelo na câmera ou num vídeo (`--fonte`) com a mesma regra de alerta, sem enviar nada nem tocar a sirene. |

**Atualizar a placa** depois de mudar código ou modelo (no PC; o pacote não leva o `.env`, a fila `pendentes/` nem o estado, que a placa mantém):

```bat
cd raspberry\tcc_producao
tar -czf placa.tgz --exclude=__pycache__ --exclude=.env --exclude=pendentes --exclude=estado_execucao.json --exclude=metricas.csv* --exclude=*.tgz .
scp placa.tgz pi@pi-tcc.local:~/
```

```bash
tar -xzf ~/placa.tgz -C ~/tcc_producao && rm ~/placa.tgz
sudo systemctl restart tcc-epi      # se estiver instalada como serviço
```

Arquivos que saíram do projeto continuam na placa até serem apagados à mão.

Se a API estiver fora do ar, os alertas ficam em `pendentes/` (no máximo `MAX_PENDENTES`) e são reenviados automaticamente a cada minuto.

**O modelo (`modelo_pessoa_epi.tflite`, ou o caminho em `MODELO_PATH`) tem 3 classes: `capacete`, `colete` e `pessoa`** (os nomes são reconhecidos em português e inglês, ver `deteccao.py`). Não existe classe "sem capacete": a infração é a **ausência** do EPI dentro da caixa de uma pessoa. Por isso:

- **Um modelo sem as três classes é recusado na partida**, em vez de rodar mudo.
- **A falta precisa durar `TEMPO_CONFIRMACAO` segundos (padrão 1,0 s) sem interrupção** antes de alertar: um capacete que o modelo deixa de ver por um quadro não é alarme.
- **Limiares de confiança** (no `.env`): pessoa **0,65**, capacete **0,50**, colete **0,65**. Nos testes, as pessoas reais vieram com 0,74 a 0,83 e as duvidosas (que apareciam e sumiam) com 0,53 a 0,56. Limiar baixo demais aceita um EPI falso (um "colete" a 53% sobre uma camiseta) e esconde a falta; alto demais recusa um EPI real visto com pouca certeza e acusa quem está equipado. **`CONFIANCA_PESSOA` nunca abaixo de 0,50:** o banco recusa infração com confiança menor.
- **Quem não dá para julgar não é acusado:** pessoa menor que `ALTURA_MINIMA_PESSOA` (120 px) ou com a cabeça cortada pela borda de cima do quadro fica como `desconhecido`.
- Na ocorrência enviada à API, a `confianca` de um EPI `ausente` é a da **pessoa** detectada (não há detecção de capacete para medir).

**Sirene:** o relé fica no **pino físico 11** (numeração BOARD, o mesmo do teste de bancada) e toca por `DURACAO_SIRENE` segundos (padrão 2) a cada alerta novo; novos alertas durante o toque são ignorados. Duas regras, ambas configuráveis no `.env`:

- **Liga em nível baixo** (`SIRENE_ATIVA_EM=baixo`, padrão): o pino é puxado para baixo para ligar. Se o seu módulo liga ao contrário, use `SIRENE_ATIVA_EM=alto`.
- **Desliga soltando o pino** (`SIRENE_DESLIGA_SOLTANDO=true`, padrão): o pino vira entrada, sem pull. Muitos módulos de relé são alimentados com 5 V mas comandados por um pino de 3,3 V, e com o pino forçado em nível **alto** o LED do optoacoplador ainda tem tensão e o relé **não desliga** (foi o caso da bancada deste projeto: só soltar o pino calava a sirene). Com `false`, o programa conduz o nível de repouso em vez de soltar, para módulos que aceitam.

Confira de ouvido com `python3 testar_sirene.py` (desligada, toca, desligada, e continua calada depois do fim do programa).

> **Depois que o programa termina.** Ao fim de um processo (Ctrl+C, `systemctl stop`, reinício programado) a biblioteca de GPIO solta o pino e ele volta ao estado de fábrica da Raspberry: entrada com **pull-down**, que num módulo sensível pode manter o relé ligado. Por isso, ao encerrar, o programa fixa o estado "solto, sem pull" **por fora do processo** com o `pinctrl` (do Raspberry Pi OS). Para conferir depois do teste: `pinctrl get 17` deve começar por `ip` (entrada). Sem o `pinctrl`, o programa avisa no terminal.
>
> **O que isso NÃO cobre** (é do hardware, não do programa): a queda de energia, o `kill -9` e a **partida da placa**, porque até o programa subir o pino fica no estado de fábrica (entrada com pull-down). Duas soluções, que se complementam:
> - **Por software (uma vez):** `echo 'gpio=17=ip,pn' | sudo tee -a /boot/firmware/config.txt` e reinicie. O firmware passa a deixar o pino 11 solto, sem pull, desde o início da partida (para outro pino, troque o número pelo GPIO BCM dele).
> - **Por hardware:** se o módulo ainda ligar sozinho, um diodo comum (1N4148) em série no fio do sinal, com o **anodo** do lado do módulo e o **catodo** do lado da Raspberry, deixa o pino se comportar como "coletor aberto": só consegue puxar para baixo, nunca empurrar tensão para o módulo. Outra saída é alimentar a parte de entrada do módulo com 3,3 V (módulos com jumper `JD-VCC`).

**Reinício programado do turno:** depois de `REINICIAR_APOS_HORAS` horas de operação (padrão **8**; `0` desliga) o programa reinicia sozinho, esperando um momento sem ninguém em cena (no máximo `REINICIO_TOLERANCIA_S`, padrão 600 s) e terminando antes os envios em andamento. `REINICIO_MODO=programa` (padrão) reabre só o `main.py`; `REINICIO_MODO=placa` faz `sudo reboot` e só vale com o serviço instalado (para o programa subir no boot). O reinício programado não conta como queda: a tela Sistema mostra "Reinícios em 8 h" separando as quedas inesperadas dos programados, e a contagem regressiva até o próximo.

**Câmera de rede:** em câmera RTSP/HTTP a abertura e a leitura têm prazo de 10 s. Uma queda de rede ou de Wi-Fi faz a leitura falhar e o programa reconecta sozinho (`[VÍDEO] Perda de sinal... Reconectando`), em vez de ficar parado sem avisar.

**Validação do modelo (mAP por classe) na tela Sistema:** depois de treinar, rode no Colab a célula abaixo e copie o `validacao_modelo.json` gerado para a pasta do programa na placa. A placa o envia no heartbeat e a tela Sistema mostra a tabela. Sem o arquivo, a tabela fica vazia (nenhum valor é inventado). O arquivo do projeto traz os valores do modelo final (43 épocas, conjunto de validação).

```python
import json
from ultralytics import YOLO
modelo = YOLO('/content/drive/MyDrive/treino_epi/v3_pessoa_epi/weights/best.pt')
r = modelo.val(data='/content/person-vest-helmet1-2/data.yaml', imgsz=640, split='test')  # sem pasta "test": split='val'
b = r.box
classes = {modelo.names[int(c)]: {"precisao": float(b.p[i]), "recall": float(b.r[i]),
                                  "map50": float(b.ap50[i]), "map50_95": float(b.ap[i])}
           for i, c in enumerate(b.ap_class_index)}
classes["todas"] = {"precisao": float(b.mp), "recall": float(b.mr), "map50": float(b.map50), "map50_95": float(b.map)}
json.dump({"modelo": "modelo_pessoa_epi.tflite", "conjunto": "test", "imagens": int(r.seen), "classes": classes},
          open('/content/validacao_modelo.json', 'w'), ensure_ascii=False, indent=1)
```

#### Métricas de desempenho e estabilidade

O mesmo conjunto de números aparece em três lugares: no terminal (ou no `journalctl` do serviço), na **tela Sistema** do painel (via heartbeat) e, a cada `INTERVALO_METRICAS` segundos (padrão 10), numa linha do `metricas.csv` (separador `;`, abre direto no Excel). O CSV é o registro local com data e hora das medições; ao passar de 5 MB vira `metricas.csv.1` e um novo começa, para não encher o cartão SD.

```
[MÉTRICAS 10s] pré 4.5 ms | inferência 60.0 ms | pós 1.5 ms | total 66 ms (p95 67) | 5.9 FPS (mín. 5.4) | borda→decisão 53 ms
[SISTEMA] CPU 58 °C (máx. 61) | limitação 0x0 | ligado há 2h10 | execução nº 1 | reinícios em 8 h: 0 (0 queda(s)) | sirene 73 ms | API 277 ms
```

| Métrica | Onde sai |
|---|---|
| Pré-processamento / Inferência / Pós-processamento (NMS) | `pré`, `inferência`, `pós` (médias do intervalo; `p95` e pior caso no CSV) |
| Tempo total por quadro | `total` (redimensionamento + pré + inferência + pós + regras) |
| FPS sustentada | `FPS` (média do intervalo) e `mín.` (pior intervalo, sem contar o aquecimento) |
| Latência ponta a ponta (borda → alerta) | `borda→decisão`, `sirene` e `API`, contados desde a captura do quadro (a sirene e o envio só aparecem quando houve alerta) |
| Temperatura em operação contínua | `CPU` e `máx.` (lidos de `/sys/class/thermal`; `limitação` vem de `vcgencmd get_throttled`, `0x0` = sem limitação) |
| Estabilidade (reinícios) | `reinícios em 8 h` e `queda(s)`, a partir de `estado_execucao.json` |
| Confiança por classe e desempenho por carga de cena | só na tela Sistema (acumulados durante a execução) |

Ao encerrar (Ctrl+C ou `systemctl stop`) o programa imprime um `[RESUMO]` com os valores de toda a execução. Com `MOSTRAR_JANELA=true` (só para depuração, com monitor) as métricas também aparecem numa faixa na janela de vídeo.

Limites: o contador só enxerga um reinício **quando o programa volta a subir**, e uma queda de energia é reconhecida pelo estado "não encerrado" da execução anterior. Temperatura e limitação só existem na Raspberry (no PC aparecem como `-`). O dashboard acrescenta até 5 s à latência percebida (consulta periódica); isso não entra nesta medição da borda.

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
| `POST` | `/api/status/heartbeat` | Raspberry 🔑 | Sinal de vida da placa, com a `telemetria` opcional (ver abaixo) |
| `GET` | `/api/status/edge` | dashboard | Placa online/offline e o último retrato da telemetria |

🔑 exige o header `x-api-key` com o valor de `EDGE_API_KEY`.

Códigos de tipo de EPI: `no-helmet` (sem capacete), `no-vest` (sem colete) e `no-helmet-no-vest` (sem capacete **e** sem colete). Quando a **mesma pessoa** está sem capacete e sem colete na mesma captura, a API grava **um único** registro `no-helmet-no-vest`, em vez de dois. Duas pessoas diferentes (uma sem capacete, outra sem colete) continuam em registros separados.

### Telemetria da placa (tela Sistema)

A cada heartbeat (30 s) a placa envia, junto do `id_dispositivo`, um objeto opcional `telemetria` com o que antes só aparecia no terminal: temperatura da CPU (e máxima), limitação térmica (`vcgencmd get_throttled`), memória e carga da CPU, FPS, tempos de pré/inferência/pós/total, latência borda → decisão / sirene / API, tempo ligado, nº da execução, reinícios e quedas em 8 h e o nome do modelo. A API **sanitiza campo a campo** (valor fora da faixa ou desconhecido é descartado, nunca recusa o heartbeat) e guarda só o último retrato em `dispositivo_borda.telemetria`; `GET /api/status/edge` o devolve em `telemetria`, com `atualizada_ha_segundos`. Também vão no heartbeat os **resultados acumulados da execução**: a confiança média por classe (capacete, colete e ausência de EPI, uma amostra por classe a cada segundo), o desempenho por quantidade de pessoas no quadro (FPS, inferência, latência borda → decisão e temperatura para 1, 2, 3 e 4 ou mais pessoas), a temperatura média, a contagem regressiva do reinício programado e, se existir, o `validacao_modelo.json` (mAP por classe). A tela **Sistema** mostra cada item num cartão (temperatura e carga com medidor, limitação térmica decodificada) e esmaece tudo quando a placa fica sem sinal.

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
npm test                                                  # API: 42 testes de integração
(cd raspberry/tcc_producao && python -m unittest discover -s tests)   # placa: 129 testes (sem câmera, modelo nem GPIO)
npm run lint                                              # frontend
```

Os testes da API usam um PostgreSQL em memória e um Cloudinary simulado: não precisam de `.env`, internet nem do banco real.

## 📝 Observações e limitações conhecidas

- **Autenticação do dashboard é simulada** (usuário fixo em `frontend/src/lib/AuthContext.jsx`). A proteção existe apenas nas rotas da placa. Para uso real, adicione login antes de expor o painel na internet.
- **Taxa de segurança** = ocorrências que não estão pendentes (`active`) ÷ total. Ocorrências "reconhecidas" contam como tratadas.
- O histórico do Git ainda contém a senha de teste da câmera, uma chave antiga do Roboflow (`teste_final_epi.py`) e fotos de infrações de versões antigas. **Troque a senha do DVR/câmera, gere uma nova chave no Roboflow e uma nova `EDGE_API_KEY`**; trocar as chaves já deixa as antigas inúteis, sem precisar reescrever o histórico. Se o repositório for público, considere torná-lo privado.
- O modelo `.tflite` precisa ter as classes de **pessoa, capacete e colete** (`person`/`helmet`/`vest`, ou os nomes em português); a falta de EPI é inferida pela ausência dentro da caixa da pessoa. Como o alerta nasce de uma não-detecção, o recall de capacete e colete do modelo define a taxa de alarmes falsos: meça-a com a câmera real, com todos equipados, antes de usar.
- **Pessoas sobrepostas** (uma atrás da outra) podem fazer o capacete de uma cair na região da cabeça da vizinha; o sistema entrega cada EPI à pessoa mais próxima, mas oclusão forte continua sendo uma fonte de erro.
