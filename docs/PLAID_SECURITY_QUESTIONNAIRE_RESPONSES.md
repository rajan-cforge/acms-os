# Plaid Security Questionnaire Responses

**Application:** ACMS (Adaptive Context Memory System)
**Date:** December 22, 2025
**Applicant Type:** Individual Developer / Personal Use

---

## Section 1: Organization & Application Overview

### 1.1 Describe your application and its use case

ACMS is a personal finance management desktop application for single-user use. It integrates with Plaid to retrieve investment holdings and transactions from personal brokerage accounts, enabling portfolio tracking, allocation analysis, and personal financial insights.

**Key characteristics:**
- Single-user desktop application (Electron-based)
- Local deployment only (no cloud hosting)
- Personal financial data management
- Not a commercial product or service

### 1.2 Who will be using this application?

Only the application owner/developer. This is a personal project for managing my own investment portfolio. No other users will access the system.

### 1.3 How many users do you expect?

One (1) - personal use only.

### 1.4 Will you be storing Plaid access tokens?

Yes. Access tokens are encrypted using Fernet (AES-256-CBC) immediately upon receipt and stored in an encrypted format in a local PostgreSQL database. Plain-text tokens are never logged or persisted.

---

## Section 2: Information Security Policy

### 2.1 Does your organization have a documented information security policy?

Yes. See attached: `SECURITY_POLICY.md`

The policy covers:
- Data classification (LOCAL_ONLY, CONFIDENTIAL, INTERNAL, PUBLIC)
- Encryption standards (AES-256 via Fernet)
- Access control procedures
- Incident response procedures
- Secure development practices

### 2.2 How do you identify and mitigate security risks?

**Risk Identification:**
- Code review for security vulnerabilities before deployment
- Review of third-party dependencies for known CVEs
- Monitoring application logs for anomalies

**Risk Mitigation:**
- Encryption at rest for all sensitive data
- Network isolation (localhost only)
- No external API exposure
- Privacy-level enforcement preventing sensitive data from reaching external services

### 2.3 How do you monitor for security incidents?

- Application-level audit logging for all data access operations
- Error logging for authentication failures and API errors
- Manual log review (appropriate for single-user personal application)

---

## Section 3: Data Security

### 3.1 How is data encrypted at rest?

All sensitive financial data is encrypted before storage:

| Data Type | Encryption Method | Key Storage |
|-----------|-------------------|-------------|
| Plaid access tokens | Fernet (AES-256-CBC + HMAC-SHA256) | Environment variable |
| Dollar amounts (market values, cost basis) | Fernet (AES-256-CBC + HMAC-SHA256) | Environment variable |
| Transaction amounts | Fernet (AES-256-CBC + HMAC-SHA256) | Environment variable |

**Implementation details:**
- Encryption occurs immediately upon data receipt, before database write
- Decryption occurs only at display time in the local application
- Encryption keys are generated using `cryptography.fernet.Fernet.generate_key()`

### 3.2 How is data encrypted in transit?

- All Plaid API calls use HTTPS/TLS 1.2+
- Internal communication between Docker containers uses Docker's internal network
- No external network transmission of financial data

### 3.3 Where is data stored?

| Component | Storage Location | Access |
|-----------|------------------|--------|
| PostgreSQL database | Local Docker volume | localhost:40432 only |
| Application files | Local filesystem | User home directory |
| Encryption keys | Environment variables | Not persisted to disk |

**No cloud storage is used.** All data remains on the local machine.

### 3.4 How long do you retain data?

| Data Type | Retention | Deletion Method |
|-----------|-----------|-----------------|
| Financial positions | Indefinite (historical tracking) | Manual user deletion |
| Transactions | Indefinite (historical tracking) | Manual user deletion |
| Access tokens | Until user disconnects account | Secure deletion via API |
| Audit logs | 90 days | Automatic rotation |

Users (in this case, only me) maintain full control over data deletion.

### 3.5 Do you share data with third parties?

**No.** Financial data is never shared with any third party.

- Data is retrieved FROM Plaid (read-only)
- Data is stored locally only
- No analytics services receive financial data
- No cloud backup services are used
- AI/LLM services explicitly blocked from receiving financial data

---

## Section 4: Access Control

### 4.1 How do you control access to sensitive data?

**Application-level controls:**
- Single-user desktop application with no multi-user access
- Local deployment only (no remote access capability)
- No web-facing interfaces for financial data

**Infrastructure controls:**
- Database requires authentication (username/password)
- Docker containers run in isolated network
- No external ports exposed for sensitive services

### 4.2 How are credentials and secrets managed?

| Secret Type | Storage Method | Rotation |
|-------------|----------------|----------|
| Plaid Client ID | Environment variable | As needed |
| Plaid Secret | Environment variable | As needed |
| Encryption Key | Environment variable | On suspected compromise |
| Database Password | Environment variable | As needed |

**Practices:**
- Secrets never committed to version control
- `.env` files in `.gitignore`
- No secrets in application logs
- No secrets in error messages

### 4.3 Do you use multi-factor authentication?

For application access: Not applicable (local desktop application, single user, no login required - relies on OS-level authentication).

For Plaid Dashboard access: Yes, MFA is enabled on my Plaid developer account.

---

## Section 5: Network Security

### 5.1 Describe your network architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE                         │
│  ┌─────────────┐     ┌─────────────────────────────┐   │
│  │  Desktop    │────▶│  API Server (localhost:40080)│   │
│  │  App (UI)   │     └─────────────────────────────┘   │
│  └─────────────┘                  │                     │
│                                   ▼                     │
│                    ┌─────────────────────────────┐     │
│                    │  PostgreSQL (localhost:40432)│     │
│                    └─────────────────────────────┘     │
│                                   │                     │
└───────────────────────────────────│─────────────────────┘
                                    │
                          HTTPS (outbound only)
                                    │
                                    ▼
                         ┌─────────────────┐
                         │   Plaid API     │
                         │ (api.plaid.com) │
                         └─────────────────┘
```

**Key points:**
- All services bind to localhost only
- Only outbound HTTPS connections to Plaid API
- No inbound connections from internet
- Docker network isolation between containers

### 5.2 Do you have a firewall?

Yes. macOS built-in firewall is enabled. Additionally:
- Docker containers do not expose ports externally
- Application services bind to 127.0.0.1 only

### 5.3 How do you protect against common web vulnerabilities?

| Vulnerability | Mitigation |
|---------------|------------|
| SQL Injection | Parameterized queries via asyncpg |
| XSS | Desktop app (Electron), no web interface |
| CSRF | CORS restricted to localhost origins |
| Authentication bypass | No network-accessible authentication |

---

## Section 6: Secure Development

### 6.1 Do you follow secure coding practices?

Yes:
- Input validation on all API endpoints
- Parameterized database queries (no string concatenation)
- No dynamic code execution from user input
- Secrets excluded from logs
- Error messages do not expose sensitive details

### 6.2 How do you manage dependencies?

- Dependencies pinned to specific versions in `requirements.txt`
- Regular review of dependency updates
- No unnecessary dependencies included
- Python virtual environment isolation

### 6.3 Do you perform security testing?

- Manual code review for security issues
- Input validation testing
- Encryption verification testing
- Appropriate for personal/development use scope

---

## Section 7: Incident Response

### 7.1 Do you have an incident response plan?

Yes. For a personal application, the incident response process is:

1. **Detection:** Monitor logs for authentication failures, API errors, unexpected behavior
2. **Containment:** Immediately revoke affected Plaid tokens via `/api/plaid/disconnect`
3. **Eradication:** Rotate encryption keys, update credentials
4. **Recovery:** Re-establish Plaid connection with new tokens
5. **Documentation:** Record incident details and remediation steps

### 7.2 How would you handle a data breach?

1. Immediately disconnect all Plaid Items (revoke access tokens)
2. Rotate all encryption keys
3. Review audit logs to understand scope
4. Re-encrypt data with new keys if needed
5. Notify Plaid if the breach involved Plaid credentials

---

## Section 8: Compliance

### 8.1 What regulations apply to your application?

As a personal finance tool processing only my own data:
- No customer PII is processed
- No GDPR/CCPA obligations (no third-party user data)
- No SOC 2 requirements (not a service provider)
- General best practices for personal data protection apply

### 8.2 Do you process data for other users/customers?

**No.** This is strictly a personal application. I am the only user, and only my own financial data is processed.

---

## Section 9: Additional Information

### 9.1 Application Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Electron (Desktop) |
| Backend | Python FastAPI |
| Database | PostgreSQL |
| Encryption | Python cryptography (Fernet) |
| Containerization | Docker |

### 9.2 Contact Information

**Developer:** [Your Name]
**Email:** [Your Email]
**Application:** ACMS - Personal Finance Manager

---

## Attachments

1. `SECURITY_POLICY.md` - Full information security policy
2. `ACMS_Financial_Constitution_Design.md` - Application architecture (optional)

---

*I certify that the information provided in this questionnaire is accurate and reflects the current security posture of my application.*

**Signature:** ____________________
**Date:** December 22, 2025
