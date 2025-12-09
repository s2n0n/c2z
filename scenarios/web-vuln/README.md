# Web Vulnerability Scenario Environment

## Specification

| Component      | Specification        | Description                                          |
| -------------- | -------------------- | ---------------------------------------------------- |
| **OS**         | Debian 11 (Bullseye) | Base image for DVWA container `vulnerables/web-dvwa` |
| **Language**   | PHP 7.4              | Server-side logic for vulnerability processing       |
| **Web Server** | Apache 2.4           | HTTP Server                                          |
| **Database**   | MySQL 5.7            | Backend database for SQL Injection targets           |

## Source Code & Reproduction

Currently, this scenario utilizes the community-standard [DVWA Docker Image](https://github.com/digininja/DVWA).

### Deployment Structure

The deployment is managed via Helm Chart located at `charts/c2z/templates/scenarios/web-vuln/`.

### Future customization

If custom vulnerabilities are needed, source code will be placed in `src/` directory here and built into a custom image.
