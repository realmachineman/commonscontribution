# Commons Contribution — Liquid Glass + Supabase

Community bartering application with Supabase authentication and a liquid glass interface using the supplied community photographs: React + Vite, Three.js / React Three Fiber / Drei, Tailwind CSS, Python standard-library API, SQLite, Dynamic wallet connectors, viem, and Solidity contracts.

## Start locally

The package includes a compiled frontend. For the quickest start, run `python3 server.py` from this folder, then open http://localhost:8000. On macOS, you can also run `bash Start.command`. No Python dependencies are needed.

To rebuild the frontend, use Node.js 22+ and Python 3.10+:

```sh
npm ci
npm run build
python3 server.py
```

Open **http://localhost:8000**. The Python server serves both the production frontend and API. Data persists in `commons.sqlite3`. The server binds only to this computer.

For frontend development, start `python3 server.py` in one terminal and `npm run dev` in another. Vite prints its localhost URL and proxies `/api` to Python.

## Current account setup

Signup, login, confirmation emails, and password recovery now use **Supabase Auth**. The package is connected to your existing Commons Contribution project. Email signup and confirmation requirements were checked against the live service. The localhost:8000 confirmation and password-reset redirects are configured. Email delivery setup and remaining live-account checks are documented in [docs/SUPABASE.md](docs/SUPABASE.md). Public settings are included in `config/supabase.public.json`; no private keys are included.

All pages now use translucent surfaces, frosted panels, rounded navigation and controls, photographic community headers, readable contrast, reduced-motion support, and responsive layouts. All three supplied community images are included. The 3D neighborhood remains interactive.

## Working application features

- Supabase email/password signup, confirmed-email sign-in, persistent sessions, sign-out, resend confirmation, password recovery, and current-password-checked updates. Python validates bearer tokens with Supabase; legacy password/cookie login is disabled.
- Member profiles with city lookup through free Open-Meteo geocoding, manual city fallback, photo URL, biography, and all 100 requested resource categories.
- Searchable marketplace, category/city/settlement filters, resource creation, exchange proposals, owner acceptance/decline, IOU deadlines, and both-party completion.
- Atomic credit settlement; neither party can finalize someone else's exchange. Fiat amounts are member-confirmed outside payments, not processed card/bank transactions.
- Contribution ledger with nominated neighbor verification; self-verification and duplicate issuance are rejected.
- Public pilot rates: equal labor hours at 15 CC/hour, produce at 2.5 CC/kg, energy at 1 CC/kWh. The deck's conflicting labor ranges are resolved in favor of equal-hour time banking. No automatic demurrage is applied.
- Dashboard with credit balance, contribution score, pending IOUs, requests, and member-confirmed fiat receipts.
- Housing pledges reserve credits; they are not actual rent payments, guaranteed redemption, or cash earnings. Withdrawal is not implemented in this pilot.
- Interactive procedural 3D island: garden beds, greenhouse, solar array, workshop, kinetic exercise station, AWG tower, mesh tower, selectable resource nodes, camera transitions, scroll rotation, water particles, and mesh pulses. Non-WebGL visitors retain all resource navigation.
- Resource output charts and contributor rankings derived from verified local records, with honest empty states instead of fabricated sensor readings.
- All seven resource routes, About, directory, dashboard, housing pool, settings, community chat, and local contact-message collection.
- Server community chat, persistent local outbox with deduplication on reconnect, and manual WebRTC offer/answer pairing for direct browser data channels. No TURN server is configured.
- Production service worker caches the app shell and visited assets; private API responses are never cached. First use requires connectivity; full offline authentication and all resource dashboards are not supported.
- White barter logo in `public/logo.png`.

## Try the full flow

1. Create and confirm Alice's Supabase account. Create and confirm Bob's account in a separate browser/profile.
2. Alice logs two labor hours and nominates Bob.
3. Bob opens Dashboard and verifies. Alice receives 30 CC.
4. Bob lists a resource for 10 CC. Alice proposes the exchange.
5. Bob accepts; both confirm completion. Alice now has 20 CC and Bob 10 CC.
6. Alice can pledge 5 CC into the housing pool and see 15 CC remaining.

Seed profiles and listings are clearly labeled samples. They cannot accept requests. Test using two accounts that you create. No default password or admin backdoor is included. Existing local identities require a reviewed migration; matching emails do not merge accounts.

## Dynamic and blockchain configuration

Copy `.env.example` to `.env.local` and fill `VITE_DYNAMIC_ENVIRONMENT_ID`. Add your localhost origin in the Dynamic dashboard and enable desired EVM, Solana, and embedded wallets. This uses the requested `DynamicContextProvider` and `DynamicWidget` SDK.

Dynamic wallet authentication and Supabase email authentication are currently separate; a connected wallet does not grant access to a Supabase-backed app account. Server-side Dynamic JWT verification/account linking is a remaining integration task. ENS and Unstoppable profile resolution are not implemented.

```sh
node scripts/compile-contracts.mjs
# Optional, only when you explicitly want to deploy to Base Sepolia with test ETH:
# export DEPLOYER_PRIVATE_KEY=<testnet-only-key>
# node scripts/deploy-contracts.mjs
```

The deployment script creates ERC-20 CONTRIB, ERC-1155 ResourceTracker, and native-token BarterEscrow, then grants the tracker minting permission. Set returned addresses in `.env.local` and rebuild. Contract actions appear in Settings when Dynamic is configured. Harvest submission requires a steward role. Escrow supports funding, acceptance, dual completion, unaccepted cancellation, and expiry refund. The buyer's confirmation forfeits timeout refund. Resolve real-world dispute policy before using this design beyond testnet.

Contracts compile, but have not been audited or tested on a live chain. Do not deposit real funds. Local CC balances and on-chain CONTRIB are separate; no automatic minting bridge or reconciliation has been implemented. Solidity whole-unit energy functions require a trusted steward; production meters need signed attestations and replay protection. Tool NFT rental deposits, organic certifications, and automatic seedling allocation require further contracts and interfaces.

## Didit

Export `DIDIT_API_KEY` and `DIDIT_WORKFLOW_ID` in the backend shell. Settings can create a hosted Didit verification session through the server. Secrets are not exposed to Vite. Settings can securely poll the provider decision for the session bound to the signed-in account. Provider status is displayed only after matching vendor_data to that account. Automated webhooks and application-wide AML policy enforcement remain required before launch.

## Off-grid boundaries

Native Bitchat: https://bitchat.free/ . There is no assumed browser Bitchat Mesh API. Browser WebBluetooth does not provide an interchangeable native BLE mesh relay. This app links to native Bitchat and implements its own browser WebRTC channel and device outbox; a native gateway is still needed to relay into Bitchat or reconcile queued offers on-chain. Peer messages are labeled unverified. Existing local-network WebRTC connections may survive internet loss; remote NAT traversal requires STUN/TURN and connectivity.

## Sensors and AWS

No fabricated live telemetry is presented. Connect actual inverter, gym, AWG, and greenhouse sensors before showing live generation, water quality, humidity, temperature, nutrients, or a sensor-driven day/night cycle. The current island is an illustrative model, not a measured digital twin. Interior workshop exploration and GLTF assets are not included; all models are procedural.

For an AWS deployment later, replace the local Python HTTP server with a production ASGI stack, run behind HTTPS, review Supabase session settings, configure SMTP and provider abuse protections, migrate SQLite for multi-instance use, and configure backups, automated KYC webhooks, wallet account binding, payment processing, and moderation of regulated resource categories. This deliverable is intentionally localhost-only, as requested.

## Validation

```sh
python3 tests.py
node scripts/compile-contracts.mjs
npm run build
```

The isolated integration tests check Supabase token verification with mocked provider responses, rejection of unconfirmed/expired identities, disabled legacy login, prevention of email-based account takeover, auth guards, nominated verification, self/duplicate verification rejection, two-party settlement, duplicate settlement rejection, insufficient balance, pledges, and outbox idempotency. The test uses a temporary database. Production build and Solidity compilation were successful during development. Live Supabase signup/email delivery still needs validation against the selected project. Browser visual QA was blocked by the environment's preview access policy and is not claimed as complete.

## Content and references

Content follows the supplied presentation's community contribution, marketplace, time banking, and housing-pool concepts. Event and sponsor branding are excluded. The deck's projections and tax claims are not repeated as established facts.

- UI reference: https://www.primeintellect.ai/
- Dynamic SDK: https://www.dynamic.xyz/docs/react/reference/providers/dynamiccontextprovider
- Didit session API: https://docs.didit.me/sessions-api/create-session
- Bitchat: https://github.com/permissionlesstech/bitchat
- City search: https://open-meteo.com/en/docs/geocoding-api
