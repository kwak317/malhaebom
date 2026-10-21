import { useEffect, useRef } from "react";

const BOTTOM_THRESHOLD_PX = 96;
const COACHING_RESULT_TOP_OFFSET_PX = 24;
const COACHING_RESULT_SELECTOR = ".coach-coaching-result-message, .coach-inline-comparison";

export function useCoachThreadAutoScroll() {
  const threadRef = useRef<HTMLDivElement | null>(null);
  const stayAtBottomRef = useRef(true);
  const readingComparisonRef = useRef(false);

  useEffect(() => {
    const thread = threadRef.current;
    if (!thread) return undefined;

    let forceLatestScroll = false;
    const releaseForcedScroll = () => { forceLatestScroll = false; };
    const browse = () => { forceLatestScroll = false; stayAtBottomRef.current = false; if (scheduledScroll !== null) window.clearTimeout(scheduledScroll); };
    const latest = () => { stayAtBottomRef.current = true; readingComparisonRef.current = false; };
    const updateScrollIntent = (event?: Event) => {
      if (forceLatestScroll || thread.dataset.historyBrowsing === "true") return;
      const remaining = thread.scrollHeight - thread.scrollTop - thread.clientHeight;
      stayAtBottomRef.current = remaining <= BOTTOM_THRESHOLD_PX;
      if (event && !stayAtBottomRef.current) thread.dataset.historyBrowsing = "manual";
      else if (stayAtBottomRef.current && thread.dataset.historyBrowsing === "manual") delete thread.dataset.historyBrowsing;
    };

    const scrollToLatestMessage = () => {
      if (!stayAtBottomRef.current) return;
      if (typeof thread.scrollTo === "function") {
        thread.scrollTo({ top: thread.scrollHeight, behavior: forceLatestScroll ? "instant" : "smooth" });
      } else {
        thread.scrollTop = thread.scrollHeight;
      }
    };

    const scrollToResult = (selector: string) => {
      forceLatestScroll = false;
      const resultMessages = thread.querySelectorAll<HTMLElement>(selector);
      const resultMessage = resultMessages[resultMessages.length - 1];
      if (!resultMessage) return;
      const threadTop = thread.getBoundingClientRect().top;
      const resultTop = resultMessage.getBoundingClientRect().top;
      const topOffset = resultMessage.matches(".coach-inline-comparison") ? 0 : COACHING_RESULT_TOP_OFFSET_PX;
      const targetTop = Math.max(0, thread.scrollTop + resultTop - threadTop - topOffset);
      if (typeof thread.scrollTo === "function") {
        thread.scrollTo({ top: targetTop, behavior: "smooth" });
      } else {
        thread.scrollTop = targetTop;
      }
    };

    let scheduledScroll: number | null = null;
    const scheduleScroll = (target: "latest" | "coaching-result" | "readme-result" | "resume-result" | "transcript-result" | "transcript-loading" | "job-result" | "comparison" | "resume-draft" | "resume-document" = "latest") => {
      if (Boolean(thread.dataset.historyBrowsing) || (target === "latest" && !stayAtBottomRef.current)) return;
      if (scheduledScroll !== null) window.clearTimeout(scheduledScroll);
      scheduledScroll = window.setTimeout(() => {
        scheduledScroll = null;
        if (thread.dataset.historyBrowsing) return;
        if (target === "resume-document") {
          scrollToResult(".resume-document-message");
        } else if (target === "resume-draft") {
          scrollToResult(".resume-draft-message, .resume-completion-form-message");
        } else if (target === "job-result") {
          scrollToResult(".coach-search-message.coach-job-search-message");
        } else if (target === "transcript-loading") {
          scrollToResult(".coach-transcript-second-loading");
        } else if (target === "transcript-result") {
          scrollToResult(".coach-transcript-normalized-result");
        } else if (target === "comparison") {
          scrollToResult(".coach-inline-comparison");
        } else if (target === "coaching-result") {
          scrollToResult(COACHING_RESULT_SELECTOR);
        } else if (target === "resume-result") {
          scrollToResult(".coach-resume-analysis-result, .coach-resume-confirmed-result");
        } else if (target === "readme-result") {
          scrollToResult(".coach-readme-analysis-result");
        } else {
          scrollToLatestMessage();
        }
      }, 0);
    };
    const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => {
      if (forceLatestScroll) scheduleScroll();
    });
    const observeMessageSizes = () => {
      resizeObserver?.disconnect();
      Array.from(thread.children).forEach((child) => resizeObserver?.observe(child));
    };
    observeMessageSizes();
    const observer = typeof MutationObserver === "undefined"
      ? null
      : new MutationObserver((records) => {
        observeMessageSizes();
        const changedElements = records.flatMap((record) => record.type === "attributes"
          ? [record.target]
          : Array.from(record.addedNodes))
          .filter((node): node is HTMLElement => node instanceof HTMLElement);
        const receivedImportedForm = changedElements.some((node) =>
          node.matches(".resume-import-form-message") || Boolean(node.querySelector(".resume-import-form-message")),
        );
        if (receivedImportedForm) {
          forceLatestScroll = true;
          delete thread.dataset.historyBrowsing;
          latest();
          scheduleScroll();
          return;
        }
        const receivedResumeDocument = changedElements.some((node) =>
          node.matches(".resume-document-message") || Boolean(node.querySelector(".resume-document-message")),
        );
        if (receivedResumeDocument) {
          forceLatestScroll = false;
          delete thread.dataset.historyBrowsing;
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("resume-document");
          return;
        }
        const receivedResumeDraft = changedElements.some((node) =>
          node.matches(".resume-draft-message, .resume-completion-form-message") || Boolean(node.querySelector(".resume-draft-message, .resume-completion-form-message")),
        );
        if (receivedResumeDraft) {
          forceLatestScroll = false;
          delete thread.dataset.historyBrowsing;
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("resume-draft");
          return;
        }
        const receivedJobLoading = changedElements.some((node) =>
          node.matches(".coach-job-search-message.coach-analysis-loading") || Boolean(node.querySelector(".coach-job-search-message.coach-analysis-loading")),
        );
        if (receivedJobLoading) {
          forceLatestScroll = true;
          delete thread.dataset.historyBrowsing;
          latest();
          scheduleScroll();
          return;
        }
        const receivedJobResult = changedElements.some((node) =>
          node.matches(".coach-search-message.coach-job-search-message") || Boolean(node.querySelector(".coach-search-message.coach-job-search-message")),
        );
        if (receivedJobResult) {
          forceLatestScroll = false;
          delete thread.dataset.historyBrowsing;
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("job-result");
          return;
        }
        const receivedSecondTranscriptLoading = changedElements.some((node) =>
          node.matches(".coach-transcript-second-loading") || Boolean(node.querySelector(".coach-transcript-second-loading")),
        );
        if (receivedSecondTranscriptLoading) {
          forceLatestScroll = false;
          delete thread.dataset.historyBrowsing;
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("transcript-loading");
          return;
        }
        const receivedTranscriptResult = changedElements.some((node) =>
          node.matches(".coach-transcript-normalized-result") || Boolean(node.querySelector(".coach-transcript-normalized-result")),
        );
        if (receivedTranscriptResult) {
          forceLatestScroll = false;
          delete thread.dataset.historyBrowsing;
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("transcript-result");
          return;
        }
        const receivedComparisonLoading = changedElements.some((node) =>
          node.matches(".coach-comparison-loading") || Boolean(node.querySelector(".coach-comparison-loading")),
        );
        if (receivedComparisonLoading) {
          forceLatestScroll = true;
          delete thread.dataset.historyBrowsing;
          latest();
          scheduleScroll();
          return;
        }
        const confirmedResume = changedElements.some((node) =>
          node.matches(".coach-resume-confirmed-result") || Boolean(node.querySelector(".coach-resume-confirmed-result")),
        );
        if (confirmedResume) {
          delete thread.dataset.historyBrowsing;
          readingComparisonRef.current = false;
          stayAtBottomRef.current = true;
          scheduleScroll();
          return;
        }
        const receivedCoachingResult = changedElements.some((node) =>
          node.matches(COACHING_RESULT_SELECTOR) || Boolean(node.querySelector(COACHING_RESULT_SELECTOR)),
        );
        if (receivedCoachingResult) {
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("coaching-result");
          return;
        }
        const receivedResumeResult = changedElements.some((node) =>
          node.matches(".coach-resume-analysis-result, .coach-resume-confirmed-result")
          || Boolean(node.querySelector(".coach-resume-analysis-result, .coach-resume-confirmed-result")),
        );
        if (receivedResumeResult) {
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("resume-result");
          return;
        }
        const receivedReadmeResult = changedElements.some((node) =>
          node.matches(".coach-readme-analysis-result") || Boolean(node.querySelector(".coach-readme-analysis-result")),
        );
        if (receivedReadmeResult) {
          forceLatestScroll = false;
          readingComparisonRef.current = true;
          stayAtBottomRef.current = false;
          scheduleScroll("readme-result");
          return;
        }
        const receivedCoachMessage = changedElements.some((node) =>
          node.matches(".coach-message-assistant, .coach-message-user") || Boolean(node.querySelector(".coach-message-assistant, .coach-message-user")),
        );
        const receivedUserMessage = records.filter((record) => record.type === "childList")
          .flatMap((record) => Array.from(record.addedNodes))
          .some((node) => node instanceof HTMLElement
            && (node.matches(".coach-message-user") || Boolean(node.querySelector(".coach-message-user"))));
        if (receivedUserMessage) {
          forceLatestScroll = true;
          delete thread.dataset.historyBrowsing;
        }
        if (forceLatestScroll) {
          latest();
          scheduleScroll();
          return;
        }
        if (receivedCoachMessage && !thread.dataset.historyBrowsing) {
          if (readingComparisonRef.current && !receivedUserMessage) return;
          readingComparisonRef.current = false;
          stayAtBottomRef.current = true;
          scheduleScroll();
        }
      });

    const nextStage = () => {
      forceLatestScroll = true;
      delete thread.dataset.historyBrowsing;
      latest();
      scheduleScroll();
    };

    const showTranscriptResult = () => {
      forceLatestScroll = false;
      delete thread.dataset.historyBrowsing;
      readingComparisonRef.current = true;
      stayAtBottomRef.current = false;
      scheduleScroll("transcript-result");
    };

    const showComparison = () => {
      forceLatestScroll = false;
      delete thread.dataset.historyBrowsing;
      readingComparisonRef.current = true;
      stayAtBottomRef.current = false;
      scheduleScroll("comparison");
    };

    updateScrollIntent();
    scheduleScroll();
    thread.addEventListener("workspace-next-stage", nextStage);
    thread.addEventListener("workspace-comparison", showComparison);
    thread.addEventListener("workspace-transcript-result", showTranscriptResult);
    thread.addEventListener("workspace-browse", browse);
    thread.addEventListener("workspace-latest", latest);
    thread.addEventListener("scroll", updateScrollIntent, { passive: true });
    thread.addEventListener("wheel", releaseForcedScroll, { passive: true });
    thread.addEventListener("touchstart", releaseForcedScroll, { passive: true });
    thread.addEventListener("pointerdown", releaseForcedScroll, { passive: true });
    thread.addEventListener("keydown", releaseForcedScroll);
    observer?.observe(thread, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["class"] });

    return () => {
      observer?.disconnect();
      resizeObserver?.disconnect();
      thread.removeEventListener("workspace-next-stage", nextStage);
      thread.removeEventListener("workspace-comparison", showComparison);
      thread.removeEventListener("workspace-transcript-result", showTranscriptResult);
      thread.removeEventListener("workspace-browse", browse);
      thread.removeEventListener("workspace-latest", latest);
      thread.removeEventListener("scroll", updateScrollIntent);
      thread.removeEventListener("wheel", releaseForcedScroll);
      thread.removeEventListener("touchstart", releaseForcedScroll);
      thread.removeEventListener("pointerdown", releaseForcedScroll);
      thread.removeEventListener("keydown", releaseForcedScroll);
      if (scheduledScroll !== null) window.clearTimeout(scheduledScroll);
    };
  }, []);

  return threadRef;
}
