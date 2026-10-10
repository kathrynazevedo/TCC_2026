-- Esquema do banco (PostgreSQL / Neon) usado pela API.
-- É seguro rodar mais de uma vez: tudo usa IF NOT EXISTS.
-- Reconstituído a partir das consultas da API; se o seu banco já existe, compare antes de aplicar.

CREATE TABLE IF NOT EXISTS area (
  id_area     SERIAL PRIMARY KEY,
  nome_area   VARCHAR(100) NOT NULL,
  descricao   TEXT
);

CREATE TABLE IF NOT EXISTS dispositivo_borda (
  id_dispositivo    SERIAL PRIMARY KEY,
  numero_serie      VARCHAR(100) NOT NULL UNIQUE,
  id_area           INTEGER REFERENCES area (id_area) ON DELETE SET NULL,
  ultima_atividade  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS infracao (
  id_infracao         SERIAL PRIMARY KEY,
  id_dispositivo      INTEGER NOT NULL REFERENCES dispositivo_borda (id_dispositivo),
  tipo_epi_ausente    VARCHAR(50) NOT NULL,                 -- 'no-helmet' | 'no-vest'
  score_confianca     NUMERIC(5, 4) NOT NULL,               -- 0 a 1
  timestamp_deteccao  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  imagem_url          TEXT,
  sincronizado_nuvem  BOOLEAN NOT NULL DEFAULT TRUE,
  status_resolucao    VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active' | 'acknowledged' | 'resolved'
  severidade          VARCHAR(20) NOT NULL DEFAULT 'high'    -- 'low' | 'medium' | 'high' | 'critical'
);

-- Ocorrência: uma captura da câmera com a cena inteira (foto + todas as pessoas e seus EPIs).
-- Cada infração nova da cena vira uma linha em "infracao" ligada a ela (id_ocorrencia + numero_pessoa).
CREATE TABLE IF NOT EXISTS ocorrencia (
  id_ocorrencia       SERIAL PRIMARY KEY,
  id_dispositivo      INTEGER NOT NULL REFERENCES dispositivo_borda (id_dispositivo),
  timestamp_deteccao  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  imagem_url          TEXT,
  total_pessoas       INTEGER NOT NULL DEFAULT 0,           -- pessoas em cena (com ou sem EPI)
  pessoas             JSONB NOT NULL DEFAULT '[]'           -- [{numero, caixa, capacete, colete}], ver validators.js
);

-- Bancos criados antes das ocorrências ganham as colunas novas (registros antigos ficam com NULL).
ALTER TABLE infracao ADD COLUMN IF NOT EXISTS id_ocorrencia INTEGER REFERENCES ocorrencia (id_ocorrencia) ON DELETE SET NULL;
ALTER TABLE infracao ADD COLUMN IF NOT EXISTS numero_pessoa INTEGER;

CREATE TABLE IF NOT EXISTS trabalhador (
  id_trabalhador  SERIAL PRIMARY KEY,
  nome            VARCHAR(150) NOT NULL,
  cargo           VARCHAR(100),
  status          VARCHAR(20) NOT NULL DEFAULT 'Ativo',
  zona            VARCHAR(100)
);

-- A listagem e as métricas ordenam/filtram por estas colunas.
CREATE INDEX IF NOT EXISTS idx_infracao_timestamp ON infracao (timestamp_deteccao DESC);
CREATE INDEX IF NOT EXISTS idx_infracao_status    ON infracao (status_resolucao);
CREATE INDEX IF NOT EXISTS idx_infracao_ocorrencia ON infracao (id_ocorrencia);
