import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Camera, Clock, AlertTriangle, Eye } from "lucide-react";
import EvidenceModal from "@/components/common/EvidenceModal";
import { formatDateTime } from "@/lib/format";
import { typeLabel } from "@/lib/violationLabels";

export default function RecentViolations({ violations = [] }) {
  const [selectedImage, setSelectedImage] = useState(null);
  const recent = violations.slice(0, 6);

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-colors">
      <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50 dark:bg-slate-800/50">
        <div>
          <h3 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <Camera className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Últimas Violações Detectadas
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Feed de evidências visuais capturadas em tempo real pelo sistema YOLO</p>
        </div>
        <Badge className="bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono text-xs dark:border-slate-700" variant="outline">
          Ao vivo
        </Badge>
      </div>

      <div className="p-4 flex-1 bg-slate-50/30 dark:bg-slate-900/50 overflow-auto">
        {recent.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 py-16">
            <AlertTriangle className="w-12 h-12 mb-3 opacity-20 text-blue-600 dark:text-blue-500" />
            <p className="font-medium text-slate-600 dark:text-slate-300 text-base">Nenhuma infração registrada.</p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">O canteiro de obras está seguro no momento.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {recent.map((v) => (
              <div key={v.id} className="group relative rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between">
                <div
                  className={`relative aspect-video bg-slate-100 dark:bg-slate-900 overflow-hidden ${v.imagem_url ? "cursor-pointer" : ""}`}
                  onClick={() => v.imagem_url && setSelectedImage(v.imagem_url)}
                >
                  {v.imagem_url ? (
                    <>
                      <img
                        src={v.imagem_url}
                        alt="Evidência da Infração"
                        loading="lazy"
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                        }}
                      />
                      <div className="absolute inset-0 bg-slate-900/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <span className="bg-white/90 dark:bg-slate-900/90 text-slate-800 dark:text-slate-200 text-xs font-medium px-2.5 py-1 rounded-md shadow-sm flex items-center gap-1.5 backdrop-blur-sm">
                          <Eye className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" /> Ampliar
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-full text-xs text-slate-400 font-medium bg-slate-200 dark:bg-slate-800">
                      Sem imagem
                    </div>
                  )}
                  <div className="absolute top-2 right-2">
                    <Badge className="bg-red-500/90 hover:bg-red-600 text-white border-none shadow-sm backdrop-blur-sm text-[10px]" variant="destructive">
                      {typeLabel(v.type)}
                    </Badge>
                  </div>
                </div>
                <div className="p-3 bg-white dark:bg-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                  <div className="flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
                    {formatDateTime(v.detected_at, "dd/MM/yyyy HH:mm:ss")}
                  </div>
                  <span className="font-medium truncate ml-2">{v.zone}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <EvidenceModal src={selectedImage} onClose={() => setSelectedImage(null)} />
    </div>
  );
}
