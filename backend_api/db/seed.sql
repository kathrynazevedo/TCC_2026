-- Dados iniciais para demonstração. Rode DEPOIS do schema.sql, uma única vez.
-- O dispositivo 1 é o ID_DISPOSITIVO padrão configurado na Raspberry Pi.

INSERT INTO area (nome_area, descricao) VALUES
  ('Zona Norte',       'Frente de obra norte, com maior circulação de operários.'),
  ('Canteiro Central', 'Área central de montagem e armação.'),
  ('Almoxarifado',     'Depósito de materiais e ferramentas.');

INSERT INTO dispositivo_borda (numero_serie, id_area)
  SELECT 'RPI-TCC-001', id_area FROM area WHERE nome_area = 'Zona Norte';

INSERT INTO trabalhador (nome, cargo, status, zona) VALUES
  ('Carlos Silva',   'Pedreiro',            'Ativo', 'Zona Norte'),
  ('Marcos Oliveira', 'Armador',            'Ativo', 'Canteiro Central'),
  ('João Pereira',   'Almoxarife',          'Ativo', 'Almoxarifado'),
  ('Ana Souza',      'Técnica de Segurança', 'Ativo', 'Zona Norte');
