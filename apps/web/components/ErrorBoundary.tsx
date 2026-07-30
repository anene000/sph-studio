"use client";

import { Component, type ReactNode } from "react";

/** Catches render errors in its subtree (e.g. a failed OBJ load inside the r3f Canvas)
 *  and shows a fallback instead of crashing the whole app ("Application error"). */
export class ErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", error);
  }

  render() {
    if (this.state.hasError) return this.props.fallback ?? null;
    return this.props.children;
  }
}
