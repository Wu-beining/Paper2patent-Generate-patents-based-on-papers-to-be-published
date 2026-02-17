"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    FileUp, Key, Upload, ChevronDown,
    FileText, Sparkles, ArrowRight, Terminal
} from "lucide-react";
import WorkflowPipeline, { StepData } from "@/components/WorkflowPipeline";
import StatusCard from "@/components/StatusCard";
import DownloadCenter from "@/components/DownloadCenter";
import LogPanel from "@/components/LogPanel";

const API_BASE = "http://localhost:8000/api";

const INITIAL_STEPS: StepData[] = [
    { id: "0", label: "PDF 预处理", status: "pending" },
    { id: "1", label: "基础构建", status: "pending" },
    { id: "2", label: "实施例撰写", status: "pending" },
    { id: "3", label: "权利要求书", status: "pending" },
    { id: "4", label: "说明书摘要", status: "pending" },
    { id: "5", label: "附图提示词", status: "pending" },
    { id: "6", label: "附图生成", status: "pending" },
];

type Phase = "hero" | "config" | "generating" | "done";

export default function Home() {
    // Phase control
    const [phase, setPhase] = useState<Phase>("hero");

    // Config State
    const [apiKey, setApiKey] = useState("");
    const [apiKeySet, setApiKeySet] = useState(false);
    const [keyChecking, setKeyChecking] = useState(false);

    // Upload State
    const [pdfFile, setPdfFile] = useState<File | null>(null);
    const [specSample, setSpecSample] = useState<File | null>(null);
    const [claimsSample, setClaimsSample] = useState<File | null>(null);
    const [abstractSample, setAbstractSample] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);

    // Workflow State
    const [taskId, setTaskId] = useState<string | null>(null);
    const [steps, setSteps] = useState<StepData[]>(INITIAL_STEPS);
    const [currentContent, setCurrentContent] = useState("");
    const [currentStepLabel, setCurrentStepLabel] = useState("等待开始");
    const [isStreaming, setIsStreaming] = useState(false);
    const [isDone, setIsDone] = useState(false);
    const [files, setFiles] = useState<Record<string, string>>({});
    const [figureCount, setFigureCount] = useState(0);
    const [error, setError] = useState("");

    // Log State
    const [logs, setLogs] = useState<string[]>([]);
    const [showLog, setShowLog] = useState(false);

    const contentRef = useRef("");

    // ===== Save API Key =====
    const handleSaveApiKey = async () => {
        if (!apiKey) return;
        setKeyChecking(true);
        try {
            const res = await fetch(`${API_BASE}/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: apiKey }),
            });
            if (res.ok) {
                setApiKeySet(true);
            }
        } catch {
            setError("无法连接后端服务，请确认后端已启动 (port 8000)");
        } finally {
            setKeyChecking(false);
        }
    };

    // ===== Upload & Start =====
    const handleStart = async () => {
        if (!pdfFile) return;
        setUploading(true);
        setError("");
        setSteps(INITIAL_STEPS);
        setCurrentContent("");
        setIsDone(false);
        setFiles({});
        setFigureCount(0);
        setLogs([]);

        const formData = new FormData();
        formData.append("file", pdfFile);
        if (specSample) formData.append("spec_sample", specSample);
        if (claimsSample) formData.append("claims_sample", claimsSample);
        if (abstractSample) formData.append("abstract_sample", abstractSample);

        try {
            const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
            const data = await res.json();
            setTaskId(data.task_id);
            setIsStreaming(true);
            contentRef.current = "";
            setPhase("generating");
            connectSSE(data.task_id);
        } catch (e) {
            setError("上传失败：" + String(e));
        } finally {
            setUploading(false);
        }
    };

    // ===== SSE Connection =====
    const connectSSE = useCallback((tid: string) => {
        const es = new EventSource(`${API_BASE}/stream/${tid}`);

        es.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);

                if (msg.type === "step") {
                    setCurrentStepLabel(msg.label);
                    setSteps((prev) =>
                        prev.map((s) => {
                            if (s.id === msg.step) return { ...s, status: "processing" as const };
                            if (parseInt(s.id) < parseInt(msg.step)) return { ...s, status: "completed" as const };
                            return s;
                        })
                    );
                    contentRef.current = "";
                    setCurrentContent("");
                }

                if (msg.type === "content") {
                    contentRef.current += msg.text;
                    setCurrentContent(contentRef.current);
                }

                if (msg.type === "file_ready") {
                    setFiles((prev) => ({ ...prev, [msg.doc_type]: msg.doc_type }));
                }

                if (msg.type === "figure_ready") {
                    setFigureCount(msg.index + 1);
                }

                if (msg.type === "log") {
                    const ts = new Date().toLocaleTimeString("zh-CN", { hour12: false });
                    setLogs((prev) => [...prev, `[${ts}] ${msg.message}`]);
                }

                if (msg.type === "error") {
                    setError(msg.message);
                    setIsStreaming(false);
                    es.close();
                }

                if (msg.type === "done") {
                    setIsStreaming(false);
                    if (msg.status === "completed") {
                        setSteps((prev) => prev.map((s) => ({ ...s, status: "completed" as const })));
                        setIsDone(true);
                        setFiles(msg.files || {});
                        setFigureCount(msg.figures || 0);
                        setPhase("done");
                    } else {
                        setError(msg.error || "任务失败");
                    }
                    es.close();
                }
            } catch (e) {
                console.error("SSE parse error:", e);
            }
        };

        es.onerror = () => {
            setIsStreaming(false);
            es.close();
        };
    }, []);

    // ===== Render =====
    return (
        <main className="relative">
            {/* Animated gradient background */}
            <div className="gradient-bg" />

            {/* Floating Log Button (visible during generating & done) */}
            {(phase === "generating" || phase === "done") && (
                <motion.button
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                    onClick={() => setShowLog((v) => !v)}
                    className={`fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-colors ${showLog
                            ? "bg-[var(--accent)] text-white"
                            : "bg-white/80 dark:bg-zinc-800/80 backdrop-blur-xl text-[var(--text-secondary)] border border-[var(--border-subtle)]"
                        }`}
                    title="查看运行日志"
                >
                    <Terminal className="w-5 h-5" />
                    {logs.length > 0 && !showLog && (
                        <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center font-medium">
                            {logs.length > 99 ? "99+" : logs.length}
                        </span>
                    )}
                </motion.button>
            )}

            {/* Log Panel Overlay */}
            <AnimatePresence>
                {showLog && (
                    <LogPanel logs={logs} onClose={() => setShowLog(false)} />
                )}
            </AnimatePresence>

            <AnimatePresence mode="wait">
                {/* ==================== HERO ==================== */}
                {phase === "hero" && (
                    <motion.section
                        key="hero"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, y: -40 }}
                        transition={{ duration: 0.6 }}
                        className="section-container"
                    >
                        <div className="flex flex-col items-center text-center max-w-2xl">
                            <motion.div
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
                                className="mb-8"
                            >
                                <div className="w-20 h-20 rounded-[22px] bg-gradient-to-br from-[var(--gradient-1)] to-[var(--gradient-2)] flex items-center justify-center shadow-lg shadow-purple-500/20 mb-6 mx-auto">
                                    <Sparkles className="w-10 h-10 text-white" />
                                </div>
                            </motion.div>

                            <motion.h1
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.2, duration: 0.7 }}
                                className="text-6xl font-bold tracking-tight mb-4 gradient-text-hero"
                            >
                                Paper2Patent
                            </motion.h1>

                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.6, duration: 0.8 }}
                                className="text-lg text-[var(--text-secondary)] mb-12 tracking-wide"
                            >
                                {"保护科研成果的最后一公里".split("").map((char, i) => (
                                    <motion.span
                                        key={i}
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.8 + i * 0.05, duration: 0.3 }}
                                    >
                                        {char}
                                    </motion.span>
                                ))}
                            </motion.p>

                            <motion.button
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 1.4, duration: 0.5 }}
                                onClick={() => setPhase("config")}
                                className="btn-primary text-base px-10 py-4 flex items-center gap-3"
                            >
                                开始使用
                                <ArrowRight className="w-5 h-5" />
                            </motion.button>

                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 2, duration: 0.5 }}
                                className="mt-20"
                            >
                                <motion.div
                                    animate={{ y: [0, 6, 0] }}
                                    transition={{ repeat: Infinity, duration: 2 }}
                                >
                                    <ChevronDown className="w-6 h-6 text-[var(--text-tertiary)]" />
                                </motion.div>
                            </motion.div>
                        </div>
                    </motion.section>
                )}

                {/* ==================== CONFIG ==================== */}
                {phase === "config" && (
                    <motion.section
                        key="config"
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96 }}
                        transition={{ duration: 0.5 }}
                        className="section-container py-12"
                        style={{ minHeight: "100vh" }}
                    >
                        <div className="w-full max-w-3xl space-y-8">
                            <motion.div
                                initial={{ y: -10, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                className="text-center mb-4"
                            >
                                <h2 className="text-3xl font-bold tracking-tight mb-2">配置中心</h2>
                                <p className="text-[var(--text-secondary)] text-sm">设置凭证，上传资源，一键启动</p>
                            </motion.div>

                            {/* API Key Card */}
                            <motion.div
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.1 }}
                                className="glass-card-static p-6"
                            >
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                                        <Key className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-[15px]">身份凭证</h3>
                                        <p className="text-xs text-[var(--text-secondary)]">OpenRouter API Key · 仅存内存</p>
                                    </div>
                                    {apiKeySet && (
                                        <span className="ml-auto text-xs px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-[var(--success)] font-medium">
                                            ✓ 已配置
                                        </span>
                                    )}
                                </div>
                                <div className="flex gap-3">
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder="sk-or-v1-xxxxxxxxxxxx"
                                        disabled={apiKeySet}
                                        className="flex-1 px-4 py-3 rounded-xl border border-[var(--border-subtle)] bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-opacity-40 transition-all disabled:opacity-50"
                                    />
                                    <button
                                        onClick={handleSaveApiKey}
                                        disabled={!apiKey || apiKeySet || keyChecking}
                                        className="btn-primary px-6 py-3 text-sm whitespace-nowrap"
                                    >
                                        {keyChecking ? "检测中..." : apiKeySet ? "已保存" : "验证"}
                                    </button>
                                </div>
                            </motion.div>

                            {/* Resource Matrix — 2x2 Grid */}
                            <motion.div
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.2 }}
                                className="glass-card-static p-6"
                            >
                                <div className="flex items-center gap-3 mb-5">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
                                        <Upload className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-[15px]">资源矩阵</h3>
                                        <p className="text-xs text-[var(--text-secondary)]">上传论文与范本文件</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <UploadCard
                                        label="论文原文"
                                        accept=".pdf"
                                        hint="PDF 格式"
                                        file={pdfFile}
                                        onFile={setPdfFile}
                                        primary
                                        className="col-span-2"
                                    />
                                    <UploadCard
                                        label="说明书范本"
                                        accept=".docx,.doc,.pdf,.txt"
                                        hint="Word / PDF"
                                        file={specSample}
                                        onFile={setSpecSample}
                                    />
                                    <UploadCard
                                        label="权利要求书范本"
                                        accept=".docx,.doc,.pdf,.txt"
                                        hint="Word / PDF"
                                        file={claimsSample}
                                        onFile={setClaimsSample}
                                    />
                                    <UploadCard
                                        label="说明书摘要范本"
                                        accept=".docx,.doc,.pdf,.txt"
                                        hint="Word / PDF"
                                        file={abstractSample}
                                        onFile={setAbstractSample}
                                        className="col-span-2 max-w-[calc(50%-0.5rem)]"
                                    />
                                </div>
                            </motion.div>

                            {error && (
                                <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
                                    ⚠️ {error}
                                </div>
                            )}

                            <motion.div
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.3 }}
                            >
                                <button
                                    onClick={handleStart}
                                    disabled={!pdfFile || !apiKeySet || uploading}
                                    className="btn-primary w-full py-4 text-base flex items-center justify-center gap-3"
                                >
                                    {uploading ? (
                                        <span className="animate-spin w-5 h-5 border-2 border-white rounded-full border-t-transparent" />
                                    ) : (
                                        <>
                                            <Sparkles className="w-5 h-5" />
                                            开始生成专利文书
                                        </>
                                    )}
                                </button>
                                {!apiKeySet && pdfFile && (
                                    <p className="text-center text-xs text-[var(--text-tertiary)] mt-2">请先配置 API Key</p>
                                )}
                            </motion.div>
                        </div>
                    </motion.section>
                )}

                {/* ==================== GENERATING ==================== */}
                {phase === "generating" && (
                    <motion.section
                        key="generating"
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.5 }}
                        className="min-h-screen flex flex-col items-center px-6 py-8"
                    >
                        <motion.div
                            initial={{ y: -10, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            className="text-center mb-8 mt-4"
                        >
                            <h2 className="text-2xl font-bold tracking-tight mb-1">生成看板</h2>
                            <p className="text-sm text-[var(--text-secondary)]">
                                {isStreaming ? "AI 正在逐步生成您的专利文书…" : "处理完成"}
                            </p>
                        </motion.div>

                        <div className="w-full max-w-5xl mb-6">
                            <WorkflowPipeline steps={steps} />
                        </div>

                        <div className="w-full max-w-5xl mb-8">
                            <StatusCard
                                title={currentStepLabel}
                                content={currentContent}
                                isStreaming={isStreaming}
                            />
                        </div>

                        {error && (
                            <div className="w-full max-w-5xl p-4 rounded-2xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm mb-8">
                                ⚠️ {error}
                            </div>
                        )}
                    </motion.section>
                )}

                {/* ==================== DONE / DELIVERY ==================== */}
                {phase === "done" && taskId && (
                    <motion.section
                        key="done"
                        initial={{ opacity: 0, scale: 0.96 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
                        className="min-h-screen flex flex-col items-center px-6 py-12"
                    >
                        <motion.div
                            initial={{ y: -20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            transition={{ delay: 0.2 }}
                            className="text-center mb-10"
                        >
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 0.3, type: "spring", stiffness: 300 }}
                                className="w-16 h-16 rounded-full bg-[var(--success-glow)] flex items-center justify-center mx-auto mb-4"
                            >
                                <span className="text-3xl">🎉</span>
                            </motion.div>
                            <h2 className="text-3xl font-bold tracking-tight mb-2">文书生成完毕</h2>
                            <p className="text-[var(--text-secondary)] text-sm">全部文档已准备就绪，可预览或下载</p>
                        </motion.div>

                        <div className="w-full max-w-5xl mb-8">
                            <WorkflowPipeline steps={steps} />
                        </div>

                        {/* Download Center + Figures */}
                        <div className="w-full max-w-3xl">
                            <DownloadCenter taskId={taskId} files={files} figureCount={figureCount} />
                        </div>

                        <motion.button
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.8 }}
                            onClick={() => {
                                setPhase("config");
                                setTaskId(null);
                                setSteps(INITIAL_STEPS);
                                setCurrentContent("");
                                setIsDone(false);
                                setFiles({});
                                setFigureCount(0);
                                setPdfFile(null);
                                setError("");
                                setLogs([]);
                            }}
                            className="btn-secondary mt-10"
                        >
                            生成新的专利文书
                        </motion.button>
                    </motion.section>
                )}
            </AnimatePresence>
        </main>
    );
}

/* ===== Upload Card Sub-Component ===== */
interface UploadCardProps {
    label: string;
    accept: string;
    hint: string;
    file: File | null;
    onFile: (f: File | null) => void;
    primary?: boolean;
    className?: string;
}

function UploadCard({ label, accept, hint, file, onFile, primary, className }: UploadCardProps) {
    return (
        <label
            className={`upload-zone ${file ? "has-file" : ""} flex flex-col items-center justify-center gap-2 ${primary ? "py-10" : "py-6"
                } cursor-pointer transition-all group ${className || ""}`}
        >
            <div className={`rounded-xl ${primary ? "p-3" : "p-2"} ${file
                ? "bg-green-100 dark:bg-green-900/20"
                : "bg-gray-100 dark:bg-zinc-800"
                } transition-colors group-hover:scale-105`}
            >
                {file ? (
                    <FileText className={`${primary ? "w-7 h-7" : "w-5 h-5"} text-[var(--success)]`} />
                ) : (
                    <FileUp className={`${primary ? "w-7 h-7" : "w-5 h-5"} text-[var(--text-secondary)]`} />
                )}
            </div>
            <div className="text-center">
                <p className={`font-medium ${primary ? "text-sm" : "text-xs"} ${file ? "text-[var(--success)]" : "text-[var(--text-primary)]"
                    }`}>
                    {file ? `✓ ${file.name}` : label}
                </p>
                <p className="text-[10px] text-[var(--text-tertiary)] mt-0.5">{hint}</p>
            </div>
            <input
                type="file"
                className="hidden"
                accept={accept}
                onChange={(e) => onFile(e.target.files?.[0] || null)}
            />
        </label>
    );
}
