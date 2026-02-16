# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to [rajan-cforge](https://github.com/rajan-cforge) via GitHub private message
3. Include as much detail as possible:
   - Type of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Architecture

ACMS is designed with privacy and security as core principles:

### Local-First Architecture
- All data storage (PostgreSQL, Weaviate, Redis) runs locally in Docker containers
- No data is sent to external services by default
- Cloud AI providers (Claude, GPT, Gemini) are explicitly optional

### Data Protection
- Encryption keys are auto-generated during installation
- OAuth tokens and API keys are stored encrypted
- PII detection prevents accidental data exposure

### Network Security
- All services bind to localhost only (127.0.0.1)
- No incoming connections required
- Outbound connections only for explicitly enabled features

## Best Practices for Users

1. **Change default passwords** - Run `./install.sh` which auto-generates secure passwords
2. **Keep Docker updated** - Security patches are important
3. **Don't expose ports** - Keep services on localhost unless necessary
4. **Review .env regularly** - Ensure no unnecessary API keys are configured
