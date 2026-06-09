"use client";

import { useEffect, useState } from "react";

import api from "@/lib/api";
import type { AnswerOut, QuestionOut, SessionStartOut } from "@/lib/types";

interface QuizState {
  sessionId: string;
  isAdaptive: boolean;
  currentQuestion: QuestionOut;
  questionNumber: number;
  total: number;
  displayNumber: number;
  selected: string | null;
  submitting: boolean;
  done: boolean;
  error: string | null;
  predictedLevel: "beginner" | "intermediate" | "advanced" | null;
  confidence: number | null;
}

export function useQuiz(initialData: SessionStartOut) {
  const [state, setState] = useState<QuizState>({
    sessionId: initialData.session_id,
    isAdaptive: initialData.is_adaptive,
    currentQuestion: initialData.question,
    questionNumber: initialData.question_number,
    total: initialData.total,
    displayNumber: 1,
    selected: null,
    submitting: false,
    done: false,
    error: null,
    predictedLevel: null,
    confidence: null,
  });
  const [questionRenderTime, setQuestionRenderTime] = useState(Date.now());

  useEffect(() => {
    setQuestionRenderTime(Date.now());
  }, [state.questionNumber]);

  function selectAnswer(letter: string) {
    if (state.submitting) return;
    setState((current) => ({ ...current, selected: letter, error: null }));
  }

  async function confirmAnswer(responseTimeMs: number): Promise<void> {
    if (!state.selected || state.submitting) return;

    setState((current) => ({ ...current, submitting: true, error: null }));

    try {
      const { data } = await api.post<AnswerOut>(`/sessions/${state.sessionId}/answers`, {
        question_number: state.questionNumber,
        chosen_answer: state.selected,
        response_time_ms: responseTimeMs,
      });

      if (data.done) {
        setState((current) => ({
          ...current,
          done: true,
          selected: null,
          submitting: false,
          predictedLevel: data.predicted_level ?? current.predictedLevel,
          confidence: data.confidence ?? current.confidence,
        }));
        return;
      }

      if (!data.question || !data.question_number || !data.total) {
        throw new Error("The server returned an incomplete question payload.");
      }

      setState((current) => ({
        ...current,
        currentQuestion: data.question!,
        questionNumber: data.question_number!,
        total: data.total!,
        displayNumber: current.displayNumber + 1,
        selected: null,
        submitting: false,
        predictedLevel: data.predicted_level ?? current.predictedLevel,
        confidence: data.confidence ?? current.confidence,
      }));
      setQuestionRenderTime(Date.now());
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not submit the answer.";
      setState((current) => ({
        ...current,
        submitting: false,
        error: message,
      }));
    }
  }

  return { state, selectAnswer, confirmAnswer, questionRenderTime };
}
