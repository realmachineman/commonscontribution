# Supabase account setup

The application now uses Supabase Auth for identity. Local password signup/login and legacy session cookies are disabled. Supabase stores passwords, confirms email, refreshes sessions, and sends password reset links. The Python API verifies the supplied access token with your project's `/auth/v1/user` endpoint before protected work and derives ownership only from the verified Supabase user ID.

## Connected project

The package is connected to the existing Commons Contribution project `jfararctqfpprsjnuliu`. Its public URL and publishable key are in `config/supabase.public.json`. No secret/service-role key is included. Environment settings may override these values.

Live read-only checks on September 21, 2026 confirmed: project healthy, email provider enabled, signup enabled, and email confirmation required. No real users were created or confirmation emails sent during testing. Full signup/login/email-delivery testing remains to be performed with an email you control.

On September 21, 2026, the dashboard Site URL was set to `http://localhost:8000`, and the exact `/auth/callback` and `/auth/reset` localhost:8000 redirect URLs were saved and visually verified. Optional Vite development redirects below have not been added. Custom SMTP was inspected and is disabled; configure an email provider before inviting community members.

## Project configuration

1. In your Supabase project, enable Email under Authentication → Sign In / Providers. Keep **Confirm email** enabled.
2. Set the Site URL to `http://localhost:8000` for the packaged app.
3. Allow these Redirect URLs:
   - `http://localhost:8000/auth/callback`
   - `http://localhost:8000/auth/reset`
   - `http://localhost:5173/auth/callback` (optional Vite development)
   - `http://localhost:5173/auth/reset` (optional Vite development)
4. The supplied package already includes the public project settings. To use a different project, copy `.env.example` to `.env.local` and set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`. No service-role or secret key is needed or accepted.
5. Restart `python3 server.py`. Public project settings are served through `/api/config`, so the bundled frontend does not need rebuilding.
6. Configure custom SMTP before inviting real users. Supabase's default mail service has restrictions and is intended for initial testing. Email confirmations/resets are subject to provider settings and rate limits.

Production redirect URLs must be added when an actual HTTPS domain is deployed. Continue using localhost for now, as requested.

## Verify real accounts

- Create an account with an email you control, click the confirmation link, and open Dashboard.
- Sign out and back in; verify that the same profile and balances appear.
- Request a password reset from Log in → Forgot your password. Follow the emailed link, set a new password, and verify login.
- Create a second verified account to test member verification and barter settlement.
- Use Settings to change a password; the current password is checked by Supabase.

No test users have been created in a real project by this package.

## Account ownership and existing data

Supabase user UUIDs identify app profiles. A verified user's name/city metadata seeds the profile on first sign-in; metadata never sets credits, reputation, or authorization. The API does not accept a client-supplied user ID.

Older local accounts and their contributions are preserved in SQLite, but cannot authenticate using their former passwords. If a Supabase user has the same email as an old profile, the app deliberately refuses automatic linking. A reviewed migration must explicitly map the verified Supabase UUID to the old profile and update all related IDs. Email equality alone never grants ownership of old balances.

This change moves **authentication** to Supabase. Marketplace records, profiles, trades, credits, messages, and housing pledges remain in the existing SQLite database served by Python. Supabase Postgres tables are not created or exposed. A database migration can be performed separately if cloud-hosted application data is wanted.

The browser holds Supabase's standard persisted session and sends the access token as a bearer token. Private API responses are not cached by the service worker. On sign-out, the app clears its displayed dashboard. Supabase access-token lifetime and revocation behavior follow project configuration; no custom instantaneous revocation guarantee is made.

## Validation performed

Five isolated Python tests cover the token boundary, rejection of forged/unconfirmed/expired identities, legacy login rejection, prevention of email-based account takeover, and complete two-member credit settlement. Provider responses are mocked. They do not substitute for a live confirmation-email test against your project.

References:
- https://supabase.com/docs/guides/auth/passwords
- https://supabase.com/docs/reference/javascript/auth-getuser
- https://supabase.com/docs/guides/auth/redirect-urls
