"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { StudentLogoutButton } from "@/components/auth/StudentLogoutButton";
import { QuestionCard } from "@/components/quiz/QuestionCard";
import { QuizProgress } from "@/components/quiz/QuizProgress";
import { QuizTimer } from "@/components/quiz/QuizTimer";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import { useQuiz } from "@/hooks/useQuiz";
import { useTimer } from "@/hooks/useTimer";
import type { SessionStartOut } from "@/lib/types";

export default function QuizPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [initialData, setInitialData] = useState<SessionStartOut | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("session_start");
    if (!raw) {
      router.replace("/dashboard");
      return;
    }
    try {
      const parsed = JSON.parse(raw) as SessionStartOut;
      if (parsed.session_id !== params.sessionId) {
        router.replace("/dashboard");
        return;
      }
      setInitialData(parsed);
    } catch {
      router.replace("/dashboard");
    }
  }, [params.sessionId, router]);

  if (!initialData) return null;

  return <QuizSessionView initialData={initialData} sessionId={params.sessionId} />;
}

const LEVEL_COLORS = {
  beginner: "bg-amber-100 text-amber-800 border-amber-200",
  intermediate: "bg-blue-100 text-blue-800 border-blue-200",
  advanced: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

function QuizSessionView({
  initialData,
  sessionId,
}: {
  initialData: SessionStartOut;
  sessionId: string;
}) {
  const router = useRouter();
  const quiz = useQuiz(initialData);
  const elapsed = useTimer(quiz.state.questionNumber);

  useEffect(() => {
    if (quiz.state.done) {
      if (quiz.state.predictedLevel) {
        sessionStorage.setItem(
          `level_${sessionId}`,
          JSON.stringify({ predictedLevel: quiz.state.predictedLevel, confidence: quiz.state.confidence }),
        );
      }
      router.replace(`/result/${sessionId}`);
    }
  }, [quiz.state.done, quiz.state.predictedLevel, quiz.state.confidence, router, sessionId]);

  const { predictedLevel, confidence, isAdaptive } = quiz.state;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 flex-col gap-3">
          <QuizProgress value={quiz.state.displayNumber} total={isAdaptive ? 20 : quiz.state.total} />
          {isAdaptive && (
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-violet-700">
                <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                Adaptive mode
              </span>
              {predictedLevel && (
                <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-all ${LEVEL_COLORS[predictedLevel]}`}>
                  {predictedLevel}
                  {confidence !== null && (
                    <span className="ml-1 opacity-70">{Math.round(confidence * 100)}%</span>
                  )}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 self-end md:self-auto">
          <QuizTimer elapsed={elapsed} />
          <Button variant="secondary" onClick={() => router.push("/dashboard")}>Cancel quiz</Button>
          <StudentLogoutButton />
        </div>
      </div>
      {quiz.state.error ? <div className="mb-4"><Toast message={quiz.state.error} tone="error" /></div> : null}
      <QuestionCard
        question={quiz.state.currentQuestion}
        selected={quiz.state.selected}
        disabled={quiz.state.submitting}
        onSelect={quiz.selectAnswer}
      />
      {quiz.state.selected ? (
        <div className="mt-6 flex justify-end">
          <Button
            variant="secondary"
            disabled={quiz.state.submitting}
            onClick={() => void quiz.confirmAnswer(Date.now() - quiz.questionRenderTime)}
          >
            {quiz.state.submitting ? "Submitting..." : "Confirm Answer"}
          </Button>
        </div>
      ) : null}
    </main>
  );
}
