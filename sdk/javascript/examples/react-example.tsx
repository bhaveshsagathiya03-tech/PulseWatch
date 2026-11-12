import { useEffect } from "react";
import { init, captureException } from "../src/index";

export function PulseWatchBootstrap() {
  useEffect(() => {
    init({ dsn: import.meta.env.VITE_PULSEWATCH_DSN, environment: import.meta.env.MODE });
  }, []);
  return null;
}

export function reportCheckoutError(error: unknown) {
  captureException(error, { feature: "checkout" });
}
