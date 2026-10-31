-- Migração para bancos em que infracao.tipo_epi_ausente é o ENUM "tipo_epi" (é o caso do Neon deste projeto).
--
-- Quando a MESMA pessoa está sem capacete e sem colete, a API grava um único registro "no-helmet-no-vest".
-- Esse valor não existia no ENUM: o Postgres recusava o INSERT e a placa recebia "500 Erro interno do servidor".
-- É seguro rodar mais de uma vez (IF NOT EXISTS) e não altera nenhum registro existente.
ALTER TYPE tipo_epi ADD VALUE IF NOT EXISTS 'no-helmet-no-vest';

-- Conferir (deve listar no-helmet, no-vest e no-helmet-no-vest):
-- SELECT unnest(enum_range(NULL::tipo_epi));
--
-- Atenção: o banco também tem CHECK (score_confianca >= 0.5) em "infracao". A placa grava a confiança da PESSOA
-- (CONFIANCA_PESSOA, padrão 0,50); abaixar esse limiar da placa para menos de 0,50 faria o banco recusar o alerta.
