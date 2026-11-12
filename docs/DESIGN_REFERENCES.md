# UI / UX Reference Notes

## Sentry issue details

Reference: https://docs.sentry.io/product/issues/issue-details/

The MVP adopts the same debugging information hierarchy without copying Sentry branding or proprietary assets: issue header and counts, clear resolve/status actions, first/last seen metadata, event navigation/history, stack trace, event context, tags, breadcrumbs and an activity log. Sentry's issue details documentation explicitly describes the header's error/user counts and actions, the event graph/filtering, and event-specific stack trace, breadcrumbs and tags.

## React Bits

The supplied component references were checked:

- Glass Icons: https://reactbits.dev/components/glass-icons
- Rubber Segment: https://reactbits.dev/micro/rubber-segment
- Pattern Waves: https://reactbits.dev/backgrounds/pattern-waves
- Liquid Ether: https://reactbits.dev/backgrounds/liquid-ether
- Tech Text: https://reactbits.dev/text-animations/tech-text

React Bits publishes installable source components through its shadcn-style component commands. The supplied host could not reach the npm registry during this build, so these external components were not downloaded or integrated. To keep the MVP build deterministic and avoid shipping unverified third-party source, the interface uses original CSS-based surfaces, focus/hover transitions, a restrained grid/glow auth backdrop, and lightweight SVG iconography instead. There is no WebGL background or cursor-following shader in this MVP; the observability tables and stack traces take precedence over motion.

## Design constraints

- Dark-first developer interface with layered near-black surfaces, restrained violet accent, semantic status colors and monospace code regions.
- Readability takes priority over glass blur and animation.
- Interactive controls use native keyboard-accessible buttons, inputs and selects.
- `prefers-reduced-motion` is respected in the stylesheet.
- No Sentry logos, screenshots, proprietary code or copied brand assets are included.
