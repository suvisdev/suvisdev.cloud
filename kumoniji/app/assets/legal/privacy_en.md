# Privacy Policy

Effective: November 27, 2026 · Operator (privacy officer): suvisdev · Contact: ssuvisdev@gmail.com

## 1. What we collect and why
| Information | When | Purpose |
|---|---|---|
| Email, password (stored as a one-way hash), nickname | Email sign-up | Account, login, verification emails; nickname shown in games |
| Google account identifier, email, profile name (used as your nickname when you first sign up) | Google login | Login, nickname |
| Device information (the device string your browser or app sends, up to 200 characters, stored as is — not currently shown anywhere, used only to check for account takeover), IP address, login time, new-device check value (one-way transformed from the device information) | Login | Preventing account takeover, new-device login alerts |
| IP address, refresh time (with a one-way transformed value of the login token used before) | Refreshing the login token to stay signed in (done automatically by the app and web) | Detecting reuse of a stolen token (telling it apart from near-simultaneous refreshes from the same place) |
| Email used to log in and IP address (failed login), internal account number (failed re-authentication or two-step code, including when logging in and when turning two-step verification on or off), failure count and time | Failed login, re-authentication or two-step code entry | Blocking repeated login attacks |
| IP address and request count | Sign-up, login and email requests (resending the verification email, password reset), even when they succeed | Limiting bursts of requests |
| IP address, device information (only if the app or browser sends a device value — the Kumoniji web and app currently do not) | Connecting to multiplayer | Keeping players on the same IP (and the same device, if a device value is present) out of the same auto-matched game (so one person cannot join one game with several accounts); held only in server memory and gone once your multiplayer connection closes and the game is cleared |
| Two-step secret and recovery codes (encrypted/hashed) | The secret when you start two-step setup (before the QR code is shown), recovery codes when you turn it on. If you do not finish setup, the secret stays until you set it up again or delete your account | Two-step verification |
| In-game currency changes, attendance and mission records | Playing | Running the game, investigating errors |
We do not store the contents of a game (hands and plays) in our database. Ongoing and recently finished games are held only in server memory so you can reconnect, and disappear when newer games push them out or the server restarts. We use no advertising or analytics tools.

## 2. Retention
- Account information and game records are kept until you delete your account and are removed immediately when you do. However, the internal account number and the sign-up, deletion request and deletion times are kept without a time limit as a record of the deletion (they do not include your email, nickname or other information that identifies you). Server backups made before you deleted your account may still contain it; backups are used only for recovering from failures. Ongoing and recently finished games (including single-player ones, with your internal account number and that game's hands and plays) exist only in server memory, so they are not removed the moment you delete your account; they disappear when newer games push them out or the server restarts. If you delete your account during a multiplayer game, your nickname (visible to the other players in that game) and the IP address and device information held in server memory remain until the server clears the game from memory (including the time after it ends when they can reconnect to see the result).
- Unverified sign-ups are deleted after 24 hours; login sessions 30 days after last use. Token refresh records (IP address, refresh time) are deleted 30 days after each refresh, or together with their login session (the record stays after logout and goes with the 30-day cleanup or account deletion).
- Anti-abuse records such as failed login, re-authentication and two-step code records (the email used to log in, IP address, internal account number, failure count and time) and request-limit records (IP address, request count) are deleted one day after the last attempt, even if you delete your account before then.
- Information left behind by another request processed at almost the same moment as your account deletion (such as an email change or two-step setup) is removed by the next cleanup run.
- Cleanup runs one hour after the previous run finishes, and a failed run is retried on the next one. Actual deletion may therefore happen more than an hour after the times above (longer if failures continue).

## 3. Sharing and processors
We do not sell or share your personal information, except that your nickname is shown to other players in the same multiplayer room or game (for Google sign-ups, your Google profile name). Your email and other details are never shown. We use these providers to run the Service:
| Provider | Role | Data sent |
|---|---|---|
| Google LLC (USA) | Sending account emails (Gmail), Google login, fonts on the web (fonts.gstatic.com) | Recipient address and email content / login requests / your IP address when fonts are downloaded |
| Cloudflare, Inc. (USA) | Site delivery, bot check after repeated login attempts (Turnstile) | IP address, browser information |
| Have I Been Pwned (Troy Hunt, Australia) | Checking whether a new password has appeared in a data breach (sign-up, password change or reset) | First 5 characters of the password's SHA-1 hash (sent by our server; never the password, email or your IP) |
These providers are outside Korea, and data is transferred to them over the internet while you use the Service. If you do not want this, do not sign up, or delete your account.

## 4. Your rights
- Under Options → Account you can change your email and password and delete your account.
- To access, correct, delete or restrict processing of your data, email us; we respond within 10 days.
- Please do not sign up if you are under 14. We delete accounts found to belong to children under 14.

## 5. Security
Passwords and two-step data are stored encrypted or hashed, and all traffic uses HTTPS. Repeated failed logins are temporarily blocked, and new-device logins trigger an alert to the account email. Accounts without an email (for example, a Google sign-up whose email is already used by another account) do not receive this alert.

## 6. Cookies
On the web we use only cookies strictly necessary for staying logged in and preventing request forgery. No advertising or tracking cookies. Device settings (language, backgrounds, sound) are stored only on your device.

## 7. Changes
We announce changes to this policy in the Service 7 days before they take effect.
