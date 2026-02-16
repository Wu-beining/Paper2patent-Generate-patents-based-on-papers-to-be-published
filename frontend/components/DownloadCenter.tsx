"use client";

import { motion } from "framer-motion";
import { FileText, Download, Package, Eye } from "lucide-react";

interface DownloadCenterProps {
    taskId: string;
    files: Record<string, string>;
}

const FILE_CONFIG = [
    { key: "specification", label: "说明书", desc: "发明专利说明书全文", icon: FileText, color: "from-blue-500 to-cyan-400" },
    { key: "claims", label: "权利要求书", desc: "独立权利要求与从属权利要求", icon: FileText, color: "from-violet-500 to-purple-400" },
    { key: "abstract", label: "说明书摘要", desc: "技术方案核心摘要", icon: FileText, color: "from-amber-500 to-orange-400" },
    { key: "visual_prompts", label: "附图提示词", desc: "专利附图生成提示词", icon: Eye, color: "from-emerald-500 to-green-400" },
];

export default function DownloadCenter({ taskId, files }: DownloadCenterProps) {
    const downloadUrl = (type: string) => `http://localhost:8000/api/download/${taskId}/${type}`;
    const availableCount = FILE_CONFIG.filter(f => f.key in files).length;

    return (
        <div className="space-y-4">
            {/* File Cards — Stack Layout */}
            <div className="space-y-3">
                {FILE_CONFIG.map(({ key, label, desc, icon: Icon, color }, index) => {
                    const ready = key in files;
                    return (
                        <motion.div
                            key={key}
                            initial={{ y: 20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            transition={{ delay: index * 0.1, duration: 0.4 }}
                        >
                            <a
                                href={ready ? downloadUrl(key) : undefined}
                                className={`download-card glass-card-static flex items-center gap-4 p-5 group ${ready ? "cursor-pointer" : "opacity-40 pointer-events-none"
                                    }`}
                            >
                                {/* Icon */}
                                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${color} flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform`}>
                                    <Icon className="w-6 h-6 text-white" />
                                </div>

                                {/* Text */}
                                <div className="flex-1 min-w-0">
                                    <p className="font-semibold text-sm text-[var(--text-primary)]">{label}</p>
                                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">{desc}</p>
                                </div>

                                {/* Download icon */}
                                {ready && (
                                    <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-zinc-800 flex items-center justify-center group-hover:bg-[var(--accent-glow)] transition-colors">
                                        <Download className="w-5 h-5 text-[var(--text-secondary)] group-hover:text-[var(--accent)] transition-colors" />
                                    </div>
                                )}
                            </a>
                        </motion.div>
                    );
                })}
            </div>

            {/* Download All Button */}
            <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.5 }}
            >
                <button
                    disabled={availableCount === 0}
                    className="btn-primary w-full py-4 text-base flex items-center justify-center gap-3"
                    onClick={() => {
                        FILE_CONFIG.forEach(({ key }) => {
                            if (key in files) {
                                const a = document.createElement("a");
                                a.href = downloadUrl(key);
                                a.download = "";
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                            }
                        });
                    }}
                >
                    <Package className="w-5 h-5" />
                    一键下载全部 ({availableCount} 份)
                </button>
            </motion.div>
        </div>
    );
}
