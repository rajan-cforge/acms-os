# ACMS Privacy Policy

**Effective Date:** December 22, 2025
**Last Updated:** December 22, 2025

---

## Overview

ACMS (Adaptive Context Memory System) is a personal desktop application for financial portfolio management. This privacy policy describes how the application handles data.

**Important:** This is a personal-use application with a single user (the developer/owner). There are no external users, customers, or consumers.

---

## Data Collection

### What We Collect

When you connect your financial accounts via Plaid, ACMS retrieves:

- Account information (account names, types)
- Investment holdings (securities, quantities, values)
- Investment transactions (buys, sells, dividends)
- Security information (ticker symbols, names, identifiers)

### How Data is Collected

Data is retrieved through the Plaid API using secure OAuth authentication. You authorize access through Plaid's Link interface, which connects directly to your financial institution.

---

## Data Storage

### Local Storage Only

All data is stored **locally on your personal computer**:

- PostgreSQL database running in Docker container
- No cloud storage or backup services
- No data transmission to external servers (except Plaid API)

### Encryption

Sensitive data is encrypted at rest:

- **Encryption Standard:** AES-256 (Fernet)
- **What's Encrypted:** Access tokens, dollar amounts, transaction values
- **Key Storage:** Local environment variables

---

## Data Usage

Your financial data is used solely for:

1. Displaying your portfolio holdings and performance
2. Tracking investment transactions
3. Generating personal financial insights
4. Portfolio allocation analysis

### AI/LLM Restriction

**Financial data is NEVER sent to external AI services.** Dollar amounts, account balances, and transaction details are explicitly excluded from any AI processing.

---

## Data Sharing

### We Do Not Share Your Data

Your financial data is **never shared** with:

- Third-party services
- Analytics providers
- Advertising networks
- Any external parties

The only external communication is with the Plaid API to retrieve your data.

---

## Data Retention

| Data Type | Retention |
|-----------|-----------|
| Holdings & Transactions | Until you delete them |
| Access Tokens | Until you disconnect the account |
| Audit Logs | 90 days |

You have full control over your data and can delete it at any time.

---

## Your Rights

As the sole user of this personal application, you can:

- **Access:** View all your stored data through the application
- **Delete:** Remove any or all data at any time
- **Disconnect:** Revoke Plaid access to your accounts
- **Export:** Access your data directly from the local database

---

## Security

We implement the following security measures:

- AES-256 encryption for sensitive data
- OAuth 2.0 for secure authentication
- Local-only deployment (no network exposure)
- Audit logging of data access

See `SECURITY_POLICY.md` for full details.

---

## Third-Party Services

### Plaid

We use Plaid to connect to your financial institutions. Plaid's privacy policy applies to their handling of your data: https://plaid.com/legal/

---

## Children's Privacy

This application is not intended for use by children under 18.

---

## Changes to This Policy

This policy may be updated when the application changes. The effective date will be updated accordingly.

---

## Contact

For questions about this privacy policy:

**Developer:** [Your Name]
**Email:** [Your Email]

---

*This privacy policy applies to the ACMS desktop application for personal financial management.*
