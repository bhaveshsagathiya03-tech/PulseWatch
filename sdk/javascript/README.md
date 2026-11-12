# PulseWatch JavaScript SDK

Local SDK source for browser, React and Next.js applications. It is intentionally not marked as published on npm.

## Install from a local checkout

```bash
npm install /path/to/PulseWatch-MVP/sdk/javascript
```

The archive includes `dist/index.js` and `dist/index.d.ts`, so the local package can be imported without running a separate SDK build. To rebuild from source, run `npm install` and `npm run build` inside `sdk/javascript/`. For a source-only integration, copy `src/index.ts` into your app and import it directly.

## React / Next.js setup

```ts
// instrumentation-client.ts (Next.js App Router, client side)
import { init } from "@pulsewatch/browser-sdk";

init({
  dsn: process.env.NEXT_PUBLIC_PULSEWATCH_DSN!,
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION,
});
```

Set `NEXT_PUBLIC_PULSEWATCH_DSN` to the DSN shown in PulseWatch project setup. Do not put an administrative credential in browser code; the project ingestion key is write-only and can only submit events.

## Manual capture

```ts
import { captureException, captureMessage, setUser, addBreadcrumb } from "@pulsewatch/browser-sdk";

setUser("customer-42");
addBreadcrumb("checkout", "Opened checkout", { plan: "standard" });
try {
  throw new Error("Payment provider timed out");
} catch (error) {
  captureException(error, { checkout: "standard" });
}
captureMessage("Checkout opened", "info", { page: "checkout" });
```
