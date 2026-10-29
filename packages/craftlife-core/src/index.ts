/**
 * @craftlife/core — public API.
 *
 * Single source of truth for the contracts shared by every CraftLife client
 * (web/desktop today, Android from M07). Enforces UPDATE_RULES.md P2:
 * there is exactly ONE implementation of domain types, money formatting,
 * server clock/time and the HTTP client contract.
 *
 * NOTE: the i18n catalogue is deliberately NOT re-exported here. It is a
 * 464 KB JSON asset that the web client fetches over HTTP at runtime
 * (`web/src/i18n.ts`) rather than bundles. Import it explicitly when a
 * consumer needs it in-process:
 *
 *     import messages from "@craftlife/core/i18n/messages.json";
 */

export * from "./types";
export * from "./utils/currency";
export * from "./utils/serverClock";
export * from "./utils/serverTime";
export * from "./api/client";
export * from "./api/platform";
