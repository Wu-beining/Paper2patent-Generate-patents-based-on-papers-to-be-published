"use client";

import { motion } from "framer-motion";
import { CheckCircle, Circle, Loader2 } from "lucide-react";

export interface StepData {
    id: string;
    label: string;
    status: "pending" | "processing" | "completed" | "failed";
}

interface WorkflowPipelineProps {
    steps: StepData[];
}

export default function WorkflowPipeline({ steps }: WorkflowPipelineProps) {
    return (
        <div className="w-full overflow-x-auto py-4 px-2 scrollbar-hide">
            <div className="flex items-center justify-center min-w-max">
                {steps.map((step, index) => {
                    // Determine connector state
                    const prevStep = index > 0 ? steps[index - 1] : null;
                    const isConnectorActive = prevStep?.status === "completed" && step.status === "processing";
                    const isConnectorDone = prevStep?.status === "completed" && step.status === "completed";

                    return (
                        <div key={step.id} className="flex items-center">
                            {/* Connector line (before each node except the first) */}
                            {index > 0 && (
                                <div
                                    className={`glow-line w-12 lg:w-20 mx-1 ${isConnectorActive ? "active" : isConnectorDone ? "completed" : ""
                                        }`}
                                />
                            )}

                            {/* Node */}
                            <motion.div
                                layout
                                initial={{ scale: 0.85, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{
                                    type: "spring",
                                    stiffness: 400,
                                    damping: 30,
                                    delay: index * 0.06,
                                }}
                                className="flex flex-col items-center gap-2"
                            >
                                <div
                                    className={`node-base ${step.status === "processing"
                                            ? "node-processing"
                                            : step.status === "completed"
                                                ? "node-completed"
                                                : step.status === "failed"
                                                    ? "border-[var(--error)] bg-red-50 dark:bg-red-950/20"
                                                    : ""
                                        }`}
                                >
                                    {step.status === "completed" ? (
                                        <motion.div
                                            initial={{ scale: 0, rotate: -180 }}
                                            animate={{ scale: 1, rotate: 0 }}
                                            transition={{ type: "spring", stiffness: 500, damping: 25 }}
                                        >
                                            <CheckCircle className="w-6 h-6 text-[var(--success)]" />
                                        </motion.div>
                                    ) : step.status === "processing" ? (
                                        <Loader2 className="w-6 h-6 text-[var(--accent)] animate-spin" />
                                    ) : (
                                        <Circle className="w-5 h-5 text-[var(--text-tertiary)]" />
                                    )}
                                </div>

                                <span
                                    className={`text-[11px] font-medium text-center leading-tight max-w-[80px] ${step.status === "pending"
                                            ? "text-[var(--text-tertiary)]"
                                            : step.status === "processing"
                                                ? "text-[var(--accent)]"
                                                : "text-[var(--text-primary)]"
                                        }`}
                                >
                                    {step.label}
                                </span>
                            </motion.div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
