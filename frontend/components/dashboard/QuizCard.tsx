import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { QuizSummaryOut } from "@/lib/types";

export function QuizCard({
  quiz,
  onStart,
  loading,
  loadingAdaptive,
}: {
  quiz: QuizSummaryOut;
  onStart: (quizId: string, adaptive?: boolean) => void;
  loading: boolean;
  loadingAdaptive?: boolean;
}) {
  return (
    <Card className="group relative flex h-full flex-col justify-between gap-6 overflow-hidden border-white/85 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(252,247,241,0.92))]">
      <div className="pointer-events-none absolute right-[-2.2rem] top-[-2.2rem] h-28 w-28 rounded-full bg-clay/10 blur-3xl transition duration-300 group-hover:bg-clay/18" />
      <div className="pointer-events-none absolute left-6 right-6 top-0 h-px bg-gradient-to-r from-transparent via-clay/30 to-transparent" />
      <div className="relative space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Quiz</p>
            <h3 className="font-heading text-2xl leading-tight text-ink">
              {quiz.display_name}
            </h3>
          </div>
          <div className="shrink-0 rounded-full border border-clay/20 bg-white/78 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-clay shadow-[0_10px_20px_rgba(217,111,61,0.08)]">
            {quiz.question_count}
          </div>
        </div>
        <div className="inline-flex w-fit rounded-full border border-ink/8 bg-white/70 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-ink/55">
          {quiz.question_count === 1 ? "Single prompt" : "Timed sequence"}
        </div>
        <p className="max-w-[28ch] text-sm leading-6 text-ink/68">
          {quiz.question_count === 1
            ? "One focused prompt ready to answer."
            : `${quiz.question_count} questions waiting for your next run.`}
        </p>
      </div>
      <div className="relative z-[1] flex flex-col gap-2 sm:flex-row">
        <Button
          className="flex-1 sm:flex-none"
          variant="secondary"
          disabled={loading || loadingAdaptive}
          onClick={() => onStart(quiz.id, true)}
          title="Questions are chosen by the ML model based on your answers"
        >
          {loadingAdaptive ? "Starting..." : "Start quiz"}
        </Button>
        <Button
          className="flex-1 sm:flex-none"
          variant="ghost"
          disabled={loading || loadingAdaptive}
          onClick={() => onStart(quiz.id, false)}
          title="Answer all questions in order"
        >
          {loading ? "Starting..." : "All questions"}
        </Button>
      </div>
    </Card>
  );
}
