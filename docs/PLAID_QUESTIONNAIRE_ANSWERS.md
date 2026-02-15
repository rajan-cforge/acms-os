# Plaid Security Questionnaire - Direct Answers

**Application:** ACMS (Personal Finance Tracker)
**Use Case:** Personal/Development - Single User

---

## Access Controls

### Question 3: What access controls does your organization have in place to limit access to production assets (physical or virtual) and sensitive data?

**Select all that apply:**
- ✅ Role-based access control (RBAC) - *Single user with full access to own data*
- ✅ Principle of least privilege - *Application only requests necessary Plaid scopes*
- ✅ Encryption of sensitive data - *AES-256 encryption for all financial data*
- ✅ Secure credential storage - *Environment variables, never in code*
- ✅ Physical security - *Personal device with full-disk encryption*

**Text explanation (if needed):**
> This is a single-user personal application running locally on my personal computer. Access is controlled through: (1) OS-level user authentication, (2) full-disk encryption on the host machine, (3) application-level encryption of all financial data using AES-256, and (4) database authentication. No remote access is available.

---

### Question 4: Does your organization provide multi-factor authentication (MFA) for consumers on the mobile and/or web applications before Plaid Link is surfaced?

**Select:** Not Applicable / No

**Text explanation:**
> This is a personal desktop application with a single user (myself). There are no "consumers" - I am the only user. The application runs locally and relies on operating system authentication (macOS login with optional TouchID/password). Plaid Link is only accessible after launching the local desktop application.

---

### Question 5: Is multi-factor authentication (MFA) in place for access to critical systems that store or process consumer financial data?

**Select:** Yes (with explanation) OR Not Applicable

**Text explanation:**
> This is a personal/development application with no "consumer" data - only my own financial data. Access to the local machine uses macOS authentication. MFA is enabled on my Plaid Dashboard account. The application itself has no network-accessible login as it runs entirely locally.

---

## Infrastructure and Network Security

### Question 6: Does your organization encrypt data in-transit between clients and servers using TLS 1.2 or better?

**Select:** Yes

**Text explanation:**
> All communication with the Plaid API uses HTTPS with TLS 1.2+. Internal communication between the desktop app and local API server occurs over localhost (127.0.0.1) with no network exposure.

---

### Question 7: Does your organization encrypt consumer data you receive from the Plaid API at-rest?

**Select:** Yes

**Text explanation:**
> All financial data received from Plaid is encrypted at rest using Fernet encryption (AES-256-CBC with HMAC-SHA256). This includes:
> - Plaid access tokens (encrypted immediately upon receipt)
> - Dollar amounts (market values, cost basis, transaction amounts)
> - All sensitive identifiers
>
> Encryption occurs before database storage. Keys are stored in environment variables, not in code or database.

---

## Development and Vulnerability Management

### Question 8: Do you actively perform vulnerability scans against your employee and contractor machines and production assets?

**Select options that apply:**
- ✅ Dependency vulnerability scanning - *Review of Python packages for CVEs*
- ✅ Code review - *Manual review for security issues*
- ✅ macOS XProtect/Gatekeeper - *Built-in malware protection*
- ❌ Automated penetration testing - *Not applicable for personal project*
- ❌ Third-party security audits - *Not applicable for personal project*

**Text explanation:**
> This is a personal development project. Security practices include: (1) manual code review for vulnerabilities, (2) review of third-party dependencies, (3) macOS built-in security (XProtect, Gatekeeper, FileVault), and (4) keeping development tools updated. Enterprise-grade vulnerability scanning is not implemented as this is a single-user personal application.

---

## Privacy

### Question 9: Does your organization have a privacy policy for the application where Plaid Link will be deployed?

**Select:** Yes (attach) OR Not Applicable

**Text explanation:**
> This is a personal application for my own use only. No external users access the system. A data handling policy is documented in SECURITY_POLICY.md which specifies:
> - All financial data stays local (never uploaded to cloud)
> - Data is encrypted at rest
> - No data sharing with third parties
> - User (myself) has full control over data deletion

**If they require a link:** You can say "Not applicable - personal/development use only, no public-facing application"

---

### Question 10: Does your organization obtain consent from consumers for the collection, processing, and storage of their data?

**Select:** Not Applicable

**Text explanation:**
> This is a personal application. I am the only user and I consent to processing my own data. There are no external consumers or users. The Plaid Link flow itself obtains my consent when I authenticate with my financial institutions.

---

### Question 11: Does your organization have a defined and enforced data deletion and retention policy?

**Select:** Yes

**Text explanation:**
> Data retention is user-controlled (I control my own data):
> - Financial data: Retained indefinitely for historical tracking, deletable at any time
> - OAuth tokens: Deleted when I disconnect an account via the application
> - Audit logs: 90-day retention with automatic rotation
> - All data is stored locally and can be fully deleted by removing the application and database volume
>
> As this is personal data under my control, I can delete it at any time. No regulatory retention requirements apply to personal financial tracking.

---

## Summary for "Personal Use" Applications

**Key points to emphasize in any free-text fields:**

1. **Personal/Development Use:** "This is a single-user personal application for managing my own investment portfolio. No external users or customers."

2. **Local Only:** "All data is stored locally on my personal computer. No cloud hosting, no external data transmission except to/from Plaid API."

3. **Encryption:** "All sensitive data is encrypted at rest using AES-256 (Fernet). Access tokens encrypted immediately upon receipt."

4. **No Data Sharing:** "Financial data is never shared with third parties. It stays on my local machine."

5. **Self-Consent:** "As the only user, I consent to processing my own financial data for personal portfolio management."

---

## If Asked About Your Technology Stack

| Component | Details |
|-----------|---------|
| Application Type | Desktop (Electron) |
| Backend | Python FastAPI |
| Database | PostgreSQL (local Docker) |
| Encryption | Fernet (AES-256-CBC + HMAC-SHA256) |
| Hosting | Local machine only |
| Users | 1 (personal use) |

---

*Use these responses as a guide. Adjust wording based on the exact question format in Plaid's system.*
