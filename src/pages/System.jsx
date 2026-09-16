import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Camera, Database, Activity, RefreshCw, Wifi, VideoOff, Cpu, Radio } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";

export default function System() {
  const { toast } = useToast();
  
  // Estados para simular a API e o Ping
  const [isRestarting, setIsRestarting] = useState(false);
  const [isPinging, setIsPinging] = useState(false);
  
  // Estados para simular a conexão com o Raspberry Pi (Edge Computing)
  const [isConnectingPi, setIsConnectingPi] = useState(false);
  const [isPiConnected, setIsPiConnected] = useState(false);

  // Simula o reinício da API Node.js
  const handleRestartAPI = () => {
    setIsRestarting(true);
    setTimeout(() => {
      setIsRestarting(false);
      toast({
        title: "API Reiniciada",
        description: "O servidor Node.js foi reiniciado com sucesso na porta 3000.",
      });
    }, 2000);
  };

  // Simula o teste de Ping do MQTT
  const handleTestPing = () => {
    setIsPinging(true);
    setTimeout(() => {
      setIsPinging(false);
      toast({
        title: "Ping do Broker MQTT",
        description: "Latência: 12ms. Broker estável e aguardando dados da placa.",
      });
    }, 1500);
  };

  // Simula o Handshake (conexão) com o Raspberry Pi via WebSocket/RTSP
  const togglePiConnection = () => {
    if (isPiConnected) {
      setIsPiConnected(false);
      toast({ 
        title: "Conexão Encerrada", 
        description: "Comunicação com o Raspberry Pi interrompida." 
      });
    } else {
      setIsConnectingPi(true);
      setTimeout(() => {
        setIsConnectingPi(false);
        setIsPiConnected(true);
        toast({ 
          title: "Placa Conectada (Edge Computing)", 
          description: "Recebendo stream RTSP e tópicos MQTT do Raspberry Pi.",
          className: "bg-green-50 border-green-200"
        });
      }, 2500);
    }
  };

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Configurações do Sistema</h1>
        <p className="text-sm text-slate-500 mt-1">Integração IoT, Motor de Inferência (YOLO) e API Local</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Painel de Integração com o Hardware (Raspberry Pi) */}
        <Card className="shadow-sm border-slate-200 bg-white flex flex-col">
          <CardHeader className="border-b border-slate-100 bg-slate-50 rounded-t-xl">
            <CardTitle className="flex items-center justify-between text-lg">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-blue-600" /> Integração de Hardware (Edge)
              </div>
              {isPiConnected && (
                <span className="flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                </span>
              )}
            </CardTitle>
            <CardDescription>Conexão com a placa processadora (Raspberry Pi / ESP32)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6 flex-1 flex flex-col">
            
            {/* Monitor do Stream Externo */}
            <div className="relative w-full aspect-video bg-slate-900 rounded-lg overflow-hidden border-2 border-slate-800 flex items-center justify-center shadow-inner font-mono">
              {!isPiConnected && !isConnectingPi && (
                <div className="absolute flex flex-col items-center text-slate-500 z-10 text-center">
                  <VideoOff className="w-10 h-10 mb-2 opacity-50 mx-auto" />
                  <span className="text-sm font-medium">Aguardando Feed Externo</span>
                  <span className="text-xs mt-1">Protocolo Esperado: RTSP/WebSocket</span>
                </div>
              )}
              
              {isConnectingPi && (
                <div className="absolute flex flex-col items-center text-blue-400 z-10">
                  <RefreshCw className="w-8 h-8 mb-3 animate-spin mx-auto" />
                  <span className="text-sm">Negociando Handshake...</span>
                </div>
              )}

              {isPiConnected && (
                <div className="absolute inset-0 flex flex-col p-4">
                  <div className="text-green-400 text-xs space-y-1">
                    <p className="flex items-center gap-2"><Radio className="w-3 h-3 animate-pulse" /> SINAL RECEBIDO</p>
                    <p>IP ORIGEM: 192.168.1.210 (Raspberry Pi 4)</p>
                    <p>IA MODEL: YOLOv8 Nano (Processamento Remoto)</p>
                    <p>STREAM: 24 FPS | DATA: MQTT Tópico /safework/alerts</p>
                  </div>
                  <div className="flex-1 flex items-center justify-center opacity-20">
                    <Camera className="w-16 h-16 text-green-500" />
                  </div>
                </div>
              )}
            </div>

            <Button 
              onClick={togglePiConnection} 
              disabled={isConnectingPi}
              variant={isPiConnected ? "destructive" : "default"}
              className={`w-full ${!isPiConnected && !isConnectingPi ? "bg-blue-600 hover:bg-blue-700" : ""}`}
            >
              {isConnectingPi ? (
                <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Conectando ao IP Externo...</>
              ) : isPiConnected ? (
                <><VideoOff className="w-4 h-4 mr-2" /> Desconectar Placa</>
              ) : (
                <><Radio className="w-4 h-4 mr-2" /> Conectar Placa (IP: 192.168.1.210)</>
              )}
            </Button>

            <div className="space-y-4 pt-4 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <Label className="flex flex-col gap-1 cursor-pointer">
                  <span className="font-semibold text-slate-800">Auto-Receber Payload MQTT</span>
                  <span className="font-normal text-xs text-slate-500">Salvar detecções no banco de dados local automaticamente</span>
                </Label>
                <Switch defaultChecked disabled={!isPiConnected} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Painel do Backend */}
        <Card className="shadow-sm border-slate-200 bg-white h-fit">
          <CardHeader className="border-b border-slate-100 bg-slate-50 rounded-t-xl">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Database className="w-5 h-5 text-blue-600" /> Banco de Dados & Rede
            </CardTitle>
            <CardDescription>Gestão da infraestrutura local (Backend)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="flex items-center justify-between">
              <Label className="flex flex-col gap-1">
                <span className="font-semibold text-slate-800">Status do Servidor Node.js</span>
                <span className="font-normal text-xs text-green-600 flex items-center gap-1">
                  <Activity className="w-3 h-3" /> Online na porta 3000
                </span>
              </Label>
              <Button variant="outline" size="sm" onClick={handleRestartAPI} disabled={isRestarting}>
                {isRestarting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
                {isRestarting ? "Reiniciando..." : "Reiniciar API"}
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <Label className="flex flex-col gap-1">
                <span className="font-semibold text-slate-800">Broker MQTT (Mosquitto)</span>
                <span className="font-normal text-xs text-slate-500">Ouvindo na porta 1883 / 9001</span>
              </Label>
              <Button variant="outline" size="sm" onClick={handleTestPing} disabled={isPinging}>
                {isPinging ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Wifi className="w-4 h-4 mr-2" />}
                {isPinging ? "Testando..." : "Testar Latência"}
              </Button>
            </div>
            
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 mt-4">
              <div className="text-xs text-slate-600 font-mono flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold">Arquitetura da Aplicação:</span>
                  <Badge variant="secondary" className="bg-slate-200">Edge Computing</Badge>
                </div>
                <div className="text-[10px] text-slate-500 leading-relaxed mt-1">
                  A IA processa o vídeo na placa remotamente. O backend local recebe apenas os metadados da detecção via MQTT, aliviando a rede.
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}