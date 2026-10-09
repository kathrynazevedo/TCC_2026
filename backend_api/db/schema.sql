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
