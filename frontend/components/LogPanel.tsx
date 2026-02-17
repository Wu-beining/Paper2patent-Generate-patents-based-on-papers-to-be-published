"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { X, Terminal } from "lucide-react";

interface LogPanelProps {
    logs: string[];
    onClose: () => void;
}

export default function LogPanel({ logs, onClose }: LogPanelProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 bottom-0 z-40 w-[420px] max-w-[90vw] flex flex-col"
            style={{
                background: "rgba(15, 15, 20, 0.95)",
                backdropFilter: "blur(30px)",
                borderLeft: "1px solid rgba(255,255,255,0.08)",
            }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <Terminal className="w-4 h-4 text-green-400" />
                    <span className="text-sm font-semibold text-white/90">运行日志</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-white/50 font-mono">
                        {logs.length}
                    </span>
                </div>
                <button
                    onClick={onClose}
                    className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/10 transition-colors"
                >
                    <X className="w-4 h-4 text-white/50" />
                </button>
            </div>

            {/* Log Body */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-[11px] leading-5 space-y-0.5"
            >
                {logs.length === 0 ? (
                    <p className="text-white/30 italic">等待日志...</p>
                ) : (
                    logs.map((line, i) => {
                        // Color coding based on content
                        let color = "text-white/60";
                        if (line.includes(">>>")) color = "text-cyan-400";
                        else if (line.includes("完成") || line.includes("成功")) color = "text-green-400";
                        else if (line.includes("失败") || line.includes("异常") || line.includes("错误")) color = "text-red-400";
                        else if (line.includes("调用模型")) color = "text-purple-400";
                        else if (line.includes("正在生成")) color = "text-amber-400";

                        return (
                            <div key={i} className={`${color} select-text`}>
                                {line}
                            </div>
                        );
                    })
                )}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-white/5 text-[10px] text-white/30 font-mono">
                Paper2Patent · Runtime Log
            </div>
        </motion.div>
    );
}
