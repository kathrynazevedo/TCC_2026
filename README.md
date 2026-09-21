<h1 align="center">
  🏗️ Sistema Inteligente de Detecção de EPIs em Obras Civis
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/YOLOv8-FF0000?style=for-the-badge&logo=ultralytics&logoColor=white" alt="YOLOv8" />
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
</p>

> **Trabalho de Conclusão de Curso (TCC)** em Ciência da Computação pela Universidade Paulista (UNIP).

Este repositório contém o código-fonte de um sistema integrado de câmera inteligente baseado em Visão Computacional. O projeto foi desenhado para monitorar canteiros de obras e identificar, em tempo real, funcionários que não estejam utilizando os Equipamentos de Proteção Individual (EPIs) obrigatórios, garantindo maior segurança no ambiente de trabalho.

---

## 🧩 Arquitetura do Sistema

A solução opera em duas frentes principais de forma assíncrona: a inferência de inteligência artificial capturando e analisando o vídeo, e o painel web para monitoramento gerencial.

| Camada | Tecnologias Utilizadas |
| :--- | :--- |
| **Visão Computacional (IA)** | Python, YOLOv8 (Ultralytics), OpenCV |
| **Interface Web (Dashboard)** | React, Vite, Tailwind CSS, Shadcn UI |
| **Backend e Dados** | Node.js (`server.js`), SQLite (`database.sqlite`) |
| **Testes e Automação** | Python (`popular_dashboard.py`), Node (`simulador.js`) |

---

## 📂 Estrutura do Repositório

O repositório é um *monorepo* que consolida o modelo de rede neural e a aplicação web. 

```text
📁 raiz-do-projeto/
├── 🤖 IA e Visão Computacional
│   ├── yolov8n.pt                # Pesos do modelo de rede neural (YOLOv8)
│   ├── teste_final_epi.py        # Script principal de captura de vídeo e detecção
│   ├── teste_webcam.py           # Script secundário para testes rápidos de hardware
│   └── popular_dashboard.py      # Script em Python para gerar dados de teste
│
├── ⚙️ Backend
│   ├── server.js                 # Servidor Node.js (API de comunicação IA <-> Web)
│   ├── database.sqlite           # Banco de dados local com registros de infrações
│   └── simulador.js              # Script Node para simular inserção contínua de dados
│
└── 💻 Frontend (Dashboard)
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx     # Visão geral de ocorrências
        │   ├── Violations.jsx    # Histórico detalhado das infrações
        │   ├── Workers.jsx       # Gestão de funcionários cadastrados
        │   └── Zones.jsx         # Mapeamento de áreas de risco da obra
        └── components/
            ├── ui/               # Biblioteca de componentes base (Shadcn UI)
            └── dashboard/        # Widgets (AlertFeed.jsx, ViolationChart.jsx)
