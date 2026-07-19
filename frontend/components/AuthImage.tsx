"use client";

import { useEffect, useState } from "react";
import { fetchAttachmentObjectUrl } from "@/lib/api";

/** Loads a private attachment with the JWT, then shows it via a blob URL. */
export function AuthImage({
  attachmentId,
  alt,
  markedForDelete,
  onRemove,
}: {
  attachmentId: number;
  alt: string;
  markedForDelete?: boolean;
  onRemove?: () => void;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchAttachmentObjectUrl(attachmentId)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setSrc(url);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachmentId]);

  if (failed) return <span className="muted">Photo unavailable</span>;
  if (!src) return <span className="muted">Loading photo…</span>;

  return (
    <div
      className={
        markedForDelete ? "photo-thumb marked-delete" : "photo-thumb"
      }
    >
      <img className="trial-photo" src={src} alt={alt} />
      {onRemove && (
        <button
          type="button"
          className="photo-remove"
          aria-label={
            markedForDelete ? "Undo remove photo" : "Remove photo"
          }
          title={markedForDelete ? "Undo remove" : "Remove"}
          onClick={onRemove}
        >
          {markedForDelete ? "↶" : "×"}
        </button>
      )}
    </div>
  );
}
