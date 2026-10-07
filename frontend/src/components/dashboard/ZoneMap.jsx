import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Camera, Clock, AlertTriangle, Eye, X } from "lucide-react";

export default function ZoneMap({ violations = [] }) {
  const [selectedImage, setSelectedImage] = useState(null);
  const recentViolations = violations.slice(0, 6);

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-colors">
      <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50 dark:bg-slate-800/50">
        <div>
          <h3 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <Camera className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
            Últimas Violações Detectadas
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Feed de evidências visuais capturadas em tempo real pelo sistema YOLO</p>
        </div>
        <Badge className="bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono text-xs dark:border-slate-700" variant="outline">
          Ao vivo
        </Badge>
      </div>

      <div className="p-4 flex-1 bg-slate-50/30 dark:bg-slate-900/50 overflow-auto">
        {recentViolations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 py-16">
            <AlertTriangle className="w-12 h-12 mb-3 opacity-20 text-blue-600 dark:text-blue-500"/>
            <p className="font-medium text-slate-600 dark:text-slate-300 text-base">Nenhuma infração registrada.</p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">O canteiro de obras está seguro no momento.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {recentViolations.map((v, idx) => {
              const imageSource = v.imagem_url;
              return (
                <div key={idx} className="group relative rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between">
                  <div className="relative aspect-video bg-slate-100 dark:bg-slate-900 overflow-hidden cursor-pointer" onClick={() => imageSource && setSelectedImage(imageSource)}>
                    {imageSource ? (
                      <img src={imageSource} alt="Evidência da Infração" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onError={(e) => { e.target.style.display = 'none'; }} />
                    ) : (
                      <div className="flex items-center justify-center h-full text-xs text-slate-400 font-medium bg-slate-200 dark:bg-slate-800 animate-pulse">
                        Processando Imagem... 
                      </div>
                    )}
                    {imageSource && (
                      <div className="absolute inset-0 bg-slate-900/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <span className="bg-white/90 dark:bg-slate-900/90 text-slate-800 dark:text-slate-200 text-xs font-medium px-2.5 py-1 rounded-md shadow-sm flex items-center gap-1.5 backdrop-blur-sm">
                          <Eye className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400"/> Ampliar
                        </span>
                      </div>
                    )}
                    <div className="absolute top-2 right-2">
                      <Badge className="bg-red-500/90 hover:bg-red-600 text-white border-none shadow-sm backdrop-blur-sm text-[10px]" variant="destructive">
                        {v.type === 'no-helmet' ? 'Sem Capacete' : v.type === 'no-vest' ? 'Sem Colete' : 'Ausência de EPI'}
                      </Badge>
                    </div>
                  </div>
                  <div className="p-3 bg-white dark:bg-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                    <div className="flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-400"/>
                      {v.detected_at ? new Date(v.detected_at).toLocaleString('pt-BR') : 'Data Indisponível'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl max-w-3xl w-full overflow-hidden border border-slate-200 dark:border-slate-800">
            <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
              <h3 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <Camera className="w-4 h-4 text-blue-600 dark:text-blue-400"/>
                Evidência Capturada pela IA
              </h3>
              <button onClick={() => setSelectedImage(null)} className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors">
                <X className="w-5 h-5 text-slate-500 dark:text-slate-400"/>
              </button>
            </div>
            <div className="bg-slate-900 flex items-center justify-center p-4 min-h-[400px]">
              <img src={selectedImage} alt="Zoom da Infração" className="max-h-[70vh] w-auto object-contain rounded-lg shadow-lg" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}