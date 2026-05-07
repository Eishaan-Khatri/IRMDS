# Security Policy

## Supported Versions

IRMDS is currently pre-1.0. Security fixes target the latest `main` branch and
the newest tagged release.

## Reporting A Vulnerability

Do not open a public issue for vulnerabilities involving secrets, authentication,
command execution, dependency compromise, or unsafe actuation behavior.

Use GitHub's private vulnerability reporting if enabled for the repository. If
that is unavailable, contact the repository owner directly and include:

- affected commit or release
- reproduction steps
- impact
- suggested fix, if known

## Current Security Boundary

IRMDS v0/v1 is not a production control system.

- Commands are dry-run only.
- The simulated `ActuationGateway` does not talk to hardware.
- API authentication is not yet a production-grade layer.
- Default Docker/demo mode is intended for local development.

Do not expose the current API directly to the public internet.

## Secret Handling

Never commit:

- `.env`
- webhook URLs
- SMTP credentials
- API tokens
- model registry credentials
- private camera/RTSP URLs

Use `.env.example` for documented variable names and safe placeholder values.
