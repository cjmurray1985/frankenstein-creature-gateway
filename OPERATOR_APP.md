# Owner Home Screen app relay

The existing signed Pi connector now transports only the explicitly listed `/operator/` static assets and owner API routes. Owner API authorization lives on the Pi: one-use256-bit pairing capability from the local admin page, separate30-day hashed owner session, Secure/HttpOnly/SameSite cookie and CSRF checks for mutations. Visitor profile and family encounter cookies never authorize the owner API. Cookie forwarding selects only the namespace for the requested surface.

No new arbitrary proxy route. Pairing issuance, local admin tokens, raw camera services and source database files remain unreachable through the public gateway. The app shell can be installed; API, camera and person data are no-store and are never service-worker cached. Pi source/app deployment and local pairing are required before using this route.

This release does not alter either visitor PIN edition, persona or voice defaults. Automated tests were not requested or run for this change; syntax and deployment/manual boundary readbacks are documented in the project evidence record.
