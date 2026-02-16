"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";

interface StatusCardProps {
    title: string;
    content: string;
    isStreaming: boolean;
    onRegenerate?: () => void;
}

export default function StatusCard({ title, content, isStreaming }: StatusCardProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [content]);

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="w-full mini-terminal"
        >
            {/* Terminal Header */}
            <div className="terminal-header">
                <div className="terminal-dot" style={{ background: "#ff5f57" }} />
                <div className="terminal-dot" style={{ background: "#febc2e" }} />
                <div className="terminal-dot" style={{ background: "#28c840" }} />
                <span className="ml-3 text-[11px] text-gray-500 font-medium tracking-wide">
                    {title}
                </span>
                {isStreaming && (
                    <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-medium">
                        ● 生成中
                    </span>
                )}
            </div>

            {/* Terminal Body */}
            <div ref={scrollRef} className="terminal-body">
                {content ? (
                    <>
                        <span className="text-blue-400 opacity-60">$ </span>
                        {content}
                        {isStreaming && <span className="typing-cursor" />}
                    </>
                ) : (
                    <span className="text-gray-600 italic">
                        <span className="text-blue-400 opacity-60">$ </span>
                        等待内容生成...
                    </span>
                )}
            </div>
        </motion.div>
    );
}
