import sqlite3 from 'sqlite3';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const dbPath = join(__dirname, 'database.sqlite');
const db = new sqlite3.Database(dbPath);

// ==========================================
// 🛡️ MEMÓRIA ANTI-FLOOD E AUTO-RESOLUÇÃO
// ==========================================
const historicoRecente = {};
const TEMPO_ESPERA_MS = 60000; // 1 minuto

const zones = ["Zona Norte", "Canteiro Central", "Almoxarifado"];
const severities = ["low", "medium", "high", "critical"];

// Regras do que a câmera pode detectar
const rules = [
    { violation: "no-helmet", correction: "has-helmet", nomeCorrecao: "Capacete" },
    { violation: "no-vest", correction: "has-vest", nomeCorrecao: "Colete" }
];

console.log("🤖 Simulador de IA Avançado Iniciado!");
console.log("✅ Filtro Anti-Flood: ATIVADO");
console.log("🔄 Auto-Resolução de Alertas: ATIVADA (Malha Fechada)\n");

// Roda a cada 4 segundos
setInterval(() => {
    const zone = zones[Math.floor(Math.random() * zones.length)];
    const rule = rules[Math.floor(Math.random() * rules.length)];

    // Rola o dado: 60% chance de Infração, 40% chance de Correção
    const isCorrection = Math.random() > 0.6;
    const agora = Date.now();

    if (isCorrection) {
        // ==========================================
        // 🟢 CÂMERA DETECTOU USO CORRETO DO EPI
        // ==========================================
        
        // Atualiza no banco todos os alertas ativos daquela infração naquela zona
        const queryUpdate = `
            UPDATE violations 
            SET status = 'resolved' 
            WHERE type = ? AND zone = ? AND status IN ('active', 'acknowledged')
        `;
        
        db.run(queryUpdate, [rule.violation, zone], function(err) {
            if (err) {
                console.error("❌ Erro ao auto-resolver:", err.message);
            } else if (this.changes > 0) { // Se ele encontrou e alterou alguma linha
                console.log(`✅ [AUTO-CORREÇÃO] Operário colocou o ${rule.nomeCorrecao} na ${zone}. ${this.changes} alerta(s) fechado(s) sozinho(s)!`);
                
                // Limpa a memória anti-flood! Assim, se ele tirar o capacete de novo 10 seg depois, o sistema apita de novo.
                delete historicoRecente[`${rule.violation}-${zone}`];
            }
        });

    } else {
        // ==========================================
        // 🔴 CÂMERA DETECTOU INFRAÇÃO
        // ==========================================
        const type = rule.violation;
        const chaveAlerta = `${type}-${zone}`;

        // 🚦 Bloqueio Anti-Flood
        if (historicoRecente[chaveAlerta] && (agora - historicoRecente[chaveAlerta] < TEMPO_ESPERA_MS)) {
            console.log(`⏳ [COOLDOWN] IA ignorou alerta repetido de ${type} na ${zone}.`);
            return;
        }

        historicoRecente[chaveAlerta] = agora; // Grava na memória
        const severity = severities[Math.floor(Math.random() * severities.length)];
        const detected_at = new Date().toISOString();

        const queryInsert = `INSERT INTO violations (type, zone, severity, status, detected_at, worker_name) VALUES (?, ?, ?, ?, ?, ?)`;
        
        db.run(queryInsert, [type, zone, severity, 'active', detected_at, 'Desconhecido'], function(err) {
            if (err) {
                console.error("❌ Erro ao inserir alerta:", err.message);
            } else {
                console.log(`⚠️ [INFRAÇÃO DETECTADA] ID: ${this.lastID} | ${type} na ${zone}`);
            }
        });
    }
}, 4000);