export type PulseWatchOptions = {
  dsn: string;
  environment?: string;
  enabled?: boolean;
  maxBreadcrumbs?: number;
  release?: string;
  beforeSend?: (event: PulseWatchEvent) => PulseWatchEvent | null;
};

export type PulseWatchBreadcrumb = {
  category: string;
  message: string;
  timestamp: string;
  level?: string;
  data?: Record<string, unknown>;
};

export type PulseWatchEvent = {
  event_id: string;
  message: string;
  exception_type: string;
  stacktrace: string;
  severity: "fatal" | "error" | "warning" | "info" | "debug";
  environment: string;
  timestamp: string;
  url?: string;
  user_id?: string;
  context: Record<string, unknown>;
  tags: Record<string, unknown>;
  breadcrumbs: PulseWatchBreadcrumb[];
};

let active: PulseWatch | null = null;

function eventId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `pw-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export class PulseWatch {
  private endpoint: string;
  private options: PulseWatchOptions;
  private tags: Record<string, unknown> = {};
  private breadcrumbs: PulseWatchBreadcrumb[] = [];
  private userId?: string;
  private installed = false;

  constructor(options: PulseWatchOptions) {
    if (!options?.dsn) throw new Error("PulseWatch requires a project DSN");
    this.options = { environment: "production", enabled: true, ...options };
    this.endpoint = options.dsn.replace(/\/$/, "");
  }

  init(): this {
    if (!this.options.enabled || this.installed || typeof window === "undefined") return this;
    this.installed = true;
    window.addEventListener("error", (event) => {
      this.captureException(event.error ?? new Error(event.message), {
        filename: event.filename, line: event.lineno, column: event.colno,
      });
    });
    window.addEventListener("popstate", () => this.addBreadcrumb("navigation", `Navigated to ${location.pathname}`));
    document.addEventListener("click", (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      const selector = `${target.tagName.toLowerCase()}${target.id ? `#${target.id}` : ""}`;
      this.addBreadcrumb("ui.click", `Clicked ${selector}`, { role: target.getAttribute("role") || undefined });
    }, true);
    window.addEventListener("unhandledrejection", (event) => {
      const reason = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      this.captureException(reason, { source: "unhandledrejection" });
    });
    return this;
  }

  setUser(userId?: string): void { this.userId = userId; }
  addBreadcrumb(category: string, message: string, data: Record<string, unknown> = {}, level = "info"): void {
    this.breadcrumbs.push({ category, message, data, level, timestamp: new Date().toISOString() });
    const max = this.options.maxBreadcrumbs ?? 20;
    if (this.breadcrumbs.length > max) this.breadcrumbs.splice(0, this.breadcrumbs.length - max);
  }

  setTag(key: string, value: unknown): void { this.tags[key] = value; }
  setTags(tags: Record<string, unknown>): void { this.tags = { ...this.tags, ...tags }; }

  captureException(error: unknown, context: Record<string, unknown> = {}): string {
    const normalized = error instanceof Error ? error : new Error(String(error));
    return this.send({
      event_id: eventId(), message: normalized.message || normalized.name,
      exception_type: normalized.name || "Error", stacktrace: normalized.stack || "",
      severity: "error", environment: this.options.environment || "production",
      timestamp: new Date().toISOString(), url: typeof location !== "undefined" ? location.href : undefined,
      user_id: this.userId, context: { ...context, userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined },
      tags: { ...this.tags, ...(this.options.release ? { release: this.options.release } : {}) },
      breadcrumbs: this.breadcrumbs.slice(-20),
    });
  }

  captureMessage(message: string, severity: PulseWatchEvent["severity"] = "info", context: Record<string, unknown> = {}): string {
    return this.send({
      event_id: eventId(), message, exception_type: "Message", stacktrace: "", severity,
      environment: this.options.environment || "production", timestamp: new Date().toISOString(),
      url: typeof location !== "undefined" ? location.href : undefined, user_id: this.userId,
      context, tags: { ...this.tags }, breadcrumbs: this.breadcrumbs.slice(-20),
    });
  }

  private send(event: PulseWatchEvent): string {
    const id = event.event_id;
    if (!this.options.enabled || typeof fetch === "undefined") return id;
    let prepared: PulseWatchEvent | null = event;
    try { prepared = this.options.beforeSend ? this.options.beforeSend(event) : event; }
    catch { return id; }
    if (!prepared) return id;
    // Monitoring must never break the application being monitored.
    void fetch(this.endpoint, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prepared), keepalive: true,
    }).catch(() => undefined);
    return id;
  }
}

export function init(options: PulseWatchOptions): PulseWatch {
  active = new PulseWatch(options).init();
  return active;
}
export function captureException(error: unknown, context?: Record<string, unknown>): string {
  return active?.captureException(error, context) ?? "";
}
export function captureMessage(message: string, severity?: PulseWatchEvent["severity"], context?: Record<string, unknown>): string {
  return active?.captureMessage(message, severity, context) ?? "";
}
export function setUser(userId?: string): void { active?.setUser(userId); }
export function setTag(key: string, value: unknown): void { active?.setTag(key, value); }
export function addBreadcrumb(category: string, message: string, data?: Record<string, unknown>, level?: string): void { active?.addBreadcrumb(category, message, data, level); }
