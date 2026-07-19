"use client";

type Props = {
  title: string;
  /** One-line “what is this” */
  summary: string;
  /** When a home cook should open this */
  when?: string;
  /** How to use it, short steps */
  steps?: string[];
  /** Optional jargon demystifiers */
  terms?: { term: string; meaning: string }[];
  defaultOpen?: boolean;
};

/**
 * Collapsible plain-language help. Keeps the page calm until someone
 * asks “what is this?” — then expands like a recipe tip card in a book.
 */
export function FeatureGuide({
  title,
  summary,
  when,
  steps,
  terms,
  defaultOpen = false,
}: Props) {
  return (
    <details className="guide" open={defaultOpen || undefined}>
      <summary className="guide-summary">
        <span className="guide-title">{title}</span>
        <span className="guide-chevron" aria-hidden>
          +
        </span>
      </summary>
      <div className="guide-body">
        <p className="guide-summary-text">{summary}</p>
        {when && (
          <p>
            <span className="guide-label">When to use</span>
            {when}
          </p>
        )}
        {steps && steps.length > 0 && (
          <div>
            <span className="guide-label">How</span>
            <ol className="guide-steps">
              {steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
          </div>
        )}
        {terms && terms.length > 0 && (
          <dl className="guide-terms">
            {terms.map((t) => (
              <div key={t.term}>
                <dt>{t.term}</dt>
                <dd>{t.meaning}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </details>
  );
}
