import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Camera, Clock, AlertTriangle, Eye, X } from "lucide-react";

export default function ZoneMap({ violations = [] }) {
  const [selectedImage, setSelectedImage] = useState(null);
  
  // Pega apenas as violações mais recentes para manter o painel dinâmico 
  // SE NÃO PEGAR É SÓ TIRAR E DEIXAR O GRAFICO, SEM FICAR BATENDO CABEÇA COM ISSO AQ
  const recentViolations = violations.slice(0, 6);

  const getImageUrl = (pathOrUrl) => {
    if (!pathOrUrl) return null;
    if (pathOrUrl.startsWith('http')) {
      return pathOrUrl;
    }
    return `http://localhost:3000/uploads/${pathOrUrl}`;
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      
      {/* Cabeçalho do Card */}
      <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <div>
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <Camera className="w-5 h-5 text-blue-600" />
            Últimas Violações Detectadas
          </h3>
          <p className="text-xs text-slate-500 mt-1">Feed de evidências visuais capturadas em tempo real pelo sistema YOLO</p>
        </div>
        <Badge variant="outline" className="bg-white text-slate-600 font-mono text-xs">
          Ao vivo
        </Badge>
      </div>

      {/* Área do Grid de Imagens */}
      <div className="p-4 flex-1 bg-slate-50/30 overflow-auto">
        {recentViolations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 py-16">
            <AlertTriangle className="w-12 h-12 mb-3 opacity-20 text-blue-600" />
            <p className="font-medium text-slate-600 text-base">Nenhuma infração registrada.</p>
            <p className="text-xs text-slate-400 mt-1">O canteiro de obras está seguro no momento.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {recentViolations.map((v, idx) => {
              const imageSource = getImageUrl(v.caminho_imagem || v.imagem_url);
              
              return (
                <div 
                  key={idx} 
                  className="group relative rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between"
                >
                  {/* Container da Imagem */}
                  <div 
                    className="relative aspect-video bg-slate-100 overflow-hidden cursor-pointer" 
                    onClick={() => imageSource && setSelectedImage(imageSource)}
                  >
                    {imageSource ? (
                      <img 
                        src={imageSource} 
                        alt="Evidência da Infração" 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-xs text-slate-400 font-medium bg-slate-200 animate-pulse">
                        Processando Imagem... 
                      </div>
                    )}

                    {/* Overlay ao passar o mouse para indicar clique */}
                    {imageSource && (
                      <div className="absolute inset-0 bg-slate-900/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <span className="bg-white/90 text-slate-800 text-xs font-medium px-2.5 py-1 rounded-md shadow-sm flex items-center gap-1.5 backdrop-blur-sm">
                          <Eye className="w-3.5 h-3.5 text-blue-600" /> Ampliar
                        </span>
                      </div>
                    )}

                    {/* Tag de Alerta Flutuante */}
                    <div className="absolute top-2 right-2">
                      <Badge variant="destructive" className="bg-red-500/90 hover:bg-red-600 text-white border-none shadow-sm backdrop-blur-sm text-[10px]">
                        {v.type === 'no-helmet' ? 'Sem Capacete' : v.type === 'no-vest' ? 'Sem Colete' : 'Ausência de EPI'}
                      </Badge>
                    </div>
                  </div>

                  {/* Rodapé do Card Limpo (Apenas a Data/Hora) */}
                  <div className="p-3 bg-white flex items-center justify-between text-xs text-slate-500">
                    <div className="flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
                      {v.detected_at ? new Date(v.detected_at).toLocaleString('pt-BR') : 'Data Indisponível'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal / Lightbox para ver a foto ampliada */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative bg-white rounded-xl shadow-2xl max-w-3xl w-full overflow-hidden border border-slate-200">
            <div className="flex justify-between items-center p-4 border-b border-slate-100 bg-slate-50">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <Camera className="w-4 h-4 text-blue-600" />
                Evidência Capturada pela IA
              </h3>
              <button 
                onClick={() => setSelectedImage(null)} 
                className="p-1 hover:bg-slate-200 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>
            <div className="bg-slate-900 flex items-center justify-center p-4 min-h-[400px]">
              <img 
                src={selectedImage} 
                alt="Zoom da Infração" 
                className="max-h-[70vh] w-auto object-contain rounded-lg shadow-lg"
              />
            </div>
          </div>
        </div>
      )}

    </div>
  );
}