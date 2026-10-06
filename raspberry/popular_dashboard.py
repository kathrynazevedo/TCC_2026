import sqlite3
from datetime import datetime, timedelta
import random

def popular_banco():
    # Conecta ao banco (se não existir, ele cria o arquivo)
    conn = sqlite3.connect('database.sqlite') 
    cursor = conn.cursor()

    print("Configurando a estrutura do banco de dados...")
    
    # 1. Cria a tabela 'violations' caso ela não exista
    # Baseado nas suas entidades: type, zone, detected_at, status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            zone TEXT NOT NULL,
            detected_at DATETIME NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    print("Gerando 50 registros de teste focados às 13:00...")

    # 2. Insere os 50 registros
    for i in range(50):
        # Gera infrações concentradas entre 12:45 e 13:20
        # (Isso vai criar o pico visual no gráfico do Dashboard)
        minuto_aleatorio = random.randint(45, 80) 
        data_base = datetime.now().replace(hour=12, minute=0, second=0)
        data_infracao = data_base + timedelta(minutes=minuto_aleatorio)
        
        # Labels que seu modelo já reconhece
        tipo = random.choice(["no-helmet", "no-vest"])
        # Zonas configuradas no seu Zones.jsx
        zona = random.choice(["Zona Norte", "Canteiro Central", "Almoxarifado"])

        cursor.execute("""
            INSERT INTO violations (type, zone, detected_at, status)
            VALUES (?, ?, ?, ?)
        """, (tipo, zona, data_infracao.strftime('%Y-%m-%d %H:%M:%S'), 'active'))

    conn.commit()
    conn.close()
    print("\n[SUCESSO] 50 registros inseridos com sucesso!")
    print("[DICA] Inicie o dashboard com 'npm run dev' para ver o gráfico.")

if __name__ == "__main__":
    popular_banco()