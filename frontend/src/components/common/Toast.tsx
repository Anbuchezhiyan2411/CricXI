import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from "lucide-react";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  addToast: (message: string, type?: ToastType) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastType = "info") => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      setToasts((prev) => [...prev, { id, type, message }]);
      setTimeout(() => {
        removeToast(id);
      }, 4000);
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      {/* Toast Render Container */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col space-y-2.5 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => {
          const icons = {
            success: <CheckCircle2 className="w-5 h-5 text-[#138A36] flex-shrink-0" />,
            error: <AlertCircle className="w-5 h-5 text-[#E53935] flex-shrink-0" />,
            warning: <AlertTriangle className="w-5 h-5 text-[#F4C430] flex-shrink-0" />,
            info: <Info className="w-5 h-5 text-cyan-400 flex-shrink-0" />,
          };

          const borders = {
            success: "border-[#138A36]/50 bg-[#12263A]",
            error: "border-[#E53935]/50 bg-[#12263A]",
            warning: "border-[#F4C430]/50 bg-[#12263A]",
            info: "border-[#1E3A5F] bg-[#12263A]",
          };

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-center justify-between p-4 rounded-2xl border-2 shadow-2xl backdrop-blur-md transition-all transform animate-in slide-in-from-bottom-5 text-white ${borders[toast.type]}`}
            >
              <div className="flex items-center space-x-3 mr-2">
                {icons[toast.type]}
                <span className="text-xs sm:text-sm font-bold text-white leading-snug">{toast.message}</span>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-[#1E3A5F]"
                aria-label="Dismiss Notification"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};
