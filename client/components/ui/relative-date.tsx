"use client";

import { useEffect, useState } from "react";
import { formatDate } from "@/lib/format";

interface RelativeDateProps {
  value: string | Date;
  fallbackMode?: "long";
  className?: string;
}

export function RelativeDate({
  value,
  fallbackMode,
  className,
}: RelativeDateProps) {
  const absoluteLabel = formatDate(value, "long");
  const [label, setLabel] = useState(() => formatDate(value, fallbackMode));

  useEffect(() => {
    const update = () => setLabel(formatDate(value, "relative"));
    update();

    const timer = window.setInterval(update, 60_000);
    return () => window.clearInterval(timer);
  }, [value]);

  return (
    <span className={className} title={absoluteLabel}>
      {label}
    </span>
  );
}
