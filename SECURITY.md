# Security Policy

This document outlines the security procedures and policies for the Automated Crypto Arbitrage Service.

## Security Overview

We take the security of this application and your funds seriously. The application is designed with a security-first mindset, but security is a shared responsibility between the application's design and the operator's secure deployment practices.

## 1. API Key Management

**Storing API keys in configuration files is a major security risk.** This application has been designed to load API keys exclusively from environment variables to prevent accidental exposure.

### How to Set API Keys

Before running the bot, you must set the API key and secret for each exchange you intend to use as environment variables. The required naming convention is:

- `{EXCHANGE_NAME_IN_UPPERCASE}_API_KEY`
- `{EXCHANGE_NAME_IN_UPPERCASE}_SECRET`

For example, if you are using `binance` and `coinbasepro` as configured in `config.yaml`, you would set the variables like this:

**On Linux/macOS:**
```bash
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_SECRET="your_binance_secret_key"
export COINBASEPRO_API_KEY="your_coinbasepro_api_key"
export COINBASEPRO_SECRET="your_coinbasepro_secret_key"
```

**On Windows:**
```powershell
$env:BINANCE_API_KEY="your_binance_api_key"
$env:BINANCE_SECRET="your_binance_secret_key"
```

## 2. IP Whitelisting (Critical Recommendation)

For the highest level of security, it is **strongly recommended** that you configure IP whitelisting for your API keys on the exchange's website.

You should restrict your API keys so they can only be used from the specific, static IP address of the server where you are running the bot. This means that even if your API keys were somehow compromised, they would be useless to an attacker operating from a different IP address.

## 3. Data Encryption

- **Data in Transit**: All communication with exchange APIs uses HTTPS and Secure WebSockets (WSS), which are encrypted with TLS.
- **Data at Rest**: Financial data within the `trades.db` database (e.g., prices, amounts, profits) is encrypted at the application level using AES encryption.

### How to Set the Database Encryption Key

To use the database, you must provide a strong password in the `DB_ENCRYPTION_KEY` environment variable. The application uses this password to derive an encryption key.

You can generate a suitable password/key using Python:
```python
import os
import base64
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
```

Set the environment variable with the generated key:

**On Linux/macOS:**
```bash
export DB_ENCRYPTION_KEY="your_generated_key_or_strong_password"
```

**On Windows:**
```powershell
$env:DB_ENCRYPTION_KEY="your_generated_key_or_strong_password"
```

## 4. User Access

The web dashboard currently has no user authentication. A full user authentication system with hashed passwords and Two-Factor Authentication (2FA) is planned for a future release.

## 5. Security Audits

This software has not yet undergone a professional, third-party security audit or penetration test. For production use with significant funds, it is recommended that you commission such an audit.

---

By running this software, you acknowledge that you understand these security principles and accept responsibility for the secure configuration and operation of the bot.

## 6. Regulatory Compliance

While the bot has been designed with security in mind, you must also be aware of the regulatory landscape.

- **KYC/AML**: Know Your Customer (KYC) and Anti-Money Laundering (AML) checks are performed by the exchanges you use, not by this software. You must ensure that your accounts on all connected exchanges are fully verified and in good standing before using this bot.

- **Local Laws**: You are responsible for researching and complying with the laws in your jurisdiction regarding automated trading and cryptocurrencies.

- **Terms of Service**: Always read and understand the Terms of Service for each exchange you connect. Some exchanges may have specific rules or restrictions regarding API usage and automated trading.
