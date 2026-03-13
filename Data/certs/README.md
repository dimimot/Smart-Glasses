# Data/certs — TLS Certificate Management (Development)

### Purpose
This directory is intended for storing **TLS certificates and private keys** for local development and testing purposes.
By default, the system is configured to look for SSL/TLS files here to enable HTTPS support on the FastAPI Gateway Server.

### Git Policy
To ensure security, this directory is included in `.gitignore`.
**Private keys (`.key`, `.pem`) should NEVER be committed to the repository.**
Only documentation (like this README) is tracked.

### Local Development (Self-Signed Certificates)
For local testing with HTTPS, you can generate a self-signed certificate pair:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
