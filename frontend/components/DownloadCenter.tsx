"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Download, Package, Eye, Image, ChevronLeft, ChevronRight } from "lucide-react";

interface DownloadCenterProps {
    taskId: string;
    files: Record<string, string>;
    figureCount?: number;
}

const FILE_CONFIG = [
    { key: "specification", label: "说明书", desc: "发明专利说明书全文", icon: FileText, color: "from-blue-500 to-cyan-400" },
    { key: "claims", label: "权利要求书", desc: "独立权利要求与从属权利要求", icon: FileText, color: "from-violet-500 to-purple-400" },
    { key: "abstract", label: "说明书摘要", desc: "技术方案核心摘要", icon: FileText, color: "from-amber-500 to-orange-400" },
    { key: "visual_prompts", label: "附图提示词", desc: "专利附图生成提示词", icon: Eye, color: "from-emerald-500 to-green-400" },
];

const API_BASE = "http://localhost:8000/api";

export default function DownloadCenter({ taskId, files, figureCount = 0 }: DownloadCenterProps) {
    const downloadUrl = (type: string) => `${API_BASE}/download/${taskId}/${type}`;
    const imageUrl = (idx: number) => `${API_BASE}/image/${taskId}/${idx}`;
    const availableCount = FILE_CONFIG.filter(f => f.key in files).length;

    const [currentFigure, setCurrentFigure] = useState(0);

    return (
        <div className="space-y-6">
            {/* File Cards */}
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
                                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${color} flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform`}>
                                    <Icon className="w-6 h-6 text-white" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-semibold text-sm text-[var(--text-primary)]">{label}</p>
                                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">{desc}</p>
                                </div>
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

            {/* Figure Gallery */}
            {figureCount > 0 && (
                <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="glass-card-static p-6"
                >
                    <div className="flex items-center gap-3 mb-5">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-rose-400 flex items-center justify-center">
                            <Image className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-[15px]">专利附图</h3>
                            <p className="text-xs text-[var(--text-secondary)]">
                                共 {figureCount} 张 · 图 {currentFigure + 1}
                            </p>
                        </div>
                    </div>

                    {/* Image Carousel */}
                    <div className="relative rounded-2xl overflow-hidden bg-white dark:bg-zinc-900 border border-[var(--border-subtle)]">
                        <div className="aspect-video relative">
                            <AnimatePresence mode="wait">
                                <motion.img
                                    key={currentFigure}
                                    src={imageUrl(currentFigure)}
                                    alt={`图${currentFigure + 1}`}
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    transition={{ duration: 0.3 }}
                                    className="w-full h-full object-contain"
                                />
                            </AnimatePresence>
                        </div>

                        {/* Navigation Arrows */}
                        {figureCount > 1 && (
                            <>
                                <button
                                    onClick={(e) => {
                                        e.preventDefault();
                                        setCurrentFigure((p) => (p - 1 + figureCount) % figureCount);
                                    }}
                                    className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/30 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/50 transition-colors"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={(e) => {
                                        e.preventDefault();
                                        setCurrentFigure((p) => (p + 1) % figureCount);
                                    }}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/30 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/50 transition-colors"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </>
                        )}
                    </div>

                    {/* Thumbnail dots */}
                    {figureCount > 1 && (
                        <div className="flex justify-center gap-2 mt-4">
                            {Array.from({ length: figureCount }, (_, i) => (
                                <button
                                    key={i}
                                    onClick={() => setCurrentFigure(i)}
                                    className={`w-2 h-2 rounded-full transition-all ${i === currentFigure
                                            ? "bg-[var(--accent)] w-6"
                                            : "bg-gray-300 dark:bg-zinc-600 hover:bg-gray-400"
                                        }`}
                                />
                            ))}
                        </div>
                    )}

                    {/* Download all figures */}
                    <div className="mt-4 flex gap-2">
                        {Array.from({ length: figureCount }, (_, i) => (
                            <a
                                key={i}
                                href={imageUrl(i)}
                                download={`图${i + 1}.png`}
                                className="flex-1 text-center text-xs py-2 rounded-xl border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors"
                            >
                                下载图{i + 1}
                            </a>
                        ))}
                    </div>
                </motion.div>
            )}

            {/* Download All Button */}
            <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.6 }}
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
                    一键下载全部文档 ({availableCount} 份)
                </button>
            </motion.div>
        </div>
    );
}
