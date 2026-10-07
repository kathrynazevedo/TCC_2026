import React, { useState, useEffect } from 'react';

export default function SistemaPainel() {
    const [isOnline, setIsOnline] = useState(false);
    const [logs, setLogs] = useState([
        `[${new Date().toLocaleTimeString()}] Sistema de diagnóstico iniciado.`
    ]);

    const IP_PLACA = "192.168.1.210";

    const adicionarLog = (mensagem) => {
        const hora = new Date().toLocaleTimeString();
        setLogs((prevLogs) => {
            const novosLogs = [...prevLogs, `[${hora}] ${mensagem}`];
            return novosLogs.slice(-50); // Mantém apenas os últimos 50 logs
        });
    };

    useEffect(() => {
        let statusAnterior = null;

        const testarConexao = async () => {
            try {
                const response = await fetch('http://localhost:3000/api/status/edge');
                const data = await response.json();
                
                setIsOnline(data.online);

                if (statusAnterior !== null && statusAnterior !== data.online) {
                    if (data.online) {
                        adicionarLog(`Conexão reestabelecida com a Edge (${IP_PLACA}). Latência: ${data.time}ms`);
                    } else {
                        adicionarLog(`⚠️ Alerta: Perda de comunicação com a Edge (${IP_PLACA}).`);
                    }
                }
                statusAnterior = data.online;

            } catch (error) {
                setIsOnline(false);
                if (statusAnterior !== false) {
                    adicionarLog("⚠️ Erro: Falha ao conectar com o Backend local (Porta 3000).");
                }
                statusAnterior = false;
            }
        };

        testarConexao();
        const intervalo = setInterval(testarConexao, 10000);

        return () => clearInterval(intervalo);
    }, []);

    return (
        <div style={{ display: "flex", gap: "20px", maxWidth: "1200px", margin: "auto", padding: "20px" }}>
            {/* Card Esquerda: Status da Placa */}
            <div style={{ background: "#1e293b", borderRadius: "8px", padding: "20px", flex: 1, boxShadow: "0 4px 6px rgba(0,0,0,0.3)", color: "#f8fafc" }}>
                <h3 style={{ marginTop: 0, color: "#38bdf8", display: "flex", alignItems: "center", gap: "10px" }}>
                    🔌 Conectividade Edge (Raspberry Pi)
                </h3>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "15px", fontSize: "16px" }}>
                    <div style={{
                        width: "12px",
                        height: "12px",
                        borderRadius: "50%",
                        background: isOnline ? "#22c55e" : "#ef4444",
                        boxShadow: isOnline ? "0 0 8px #22c55e" : "0 0 8px #ef4444",
                        transition: "all 0.3s ease"
                    }} />
                    <span>
                        Status da Placa (IP: <strong>{IP_PLACA}</strong>): {isOnline ? "Online (Ativa)" : "Offline (Inalcançável)"}
                    </span>
                </div>
                <p style={{ color: "#94a3b8", fontSize: "14px" }}>
                    O backend Node.js realiza verificações periódicas para atestar a comunicação real com o hardware na borda.
                </p>
            </div>

            {/* Card Direita: Logs de Eventos / Terminal */}
            <div style={{ background: "#1e293b", borderRadius: "8px", padding: "20px", flex: 1, boxShadow: "0 4px 6px rgba(0,0,0,0.3)", color: "#f8fafc" }}>
                <h3 style={{ marginTop: 0, color: "#38bdf8", display: "flex", alignItems: "center", gap: "10px" }}>
                    💻 Logs do Diagnóstico
                </h3>
                <div style={{
                    background: "#090d16",
                    color: "#22c55e",
                    fontFamily: "monospace",
                    padding: "15px",
                    borderRadius: "6px",
                    height: "200px",
                    overflowY: "auto",
                    fontSize: "13px",
                    border: "1px solid #334155"
                }}>
                    {logs.map((log, index) => (
                        <div key={index} style={{ marginBottom: "5px" }}>{log}</div>
                    ))}
                </div>
            </div>
        </div>
    );
}