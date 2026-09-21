# Security policy

## Supported version

Security fixes are currently applied to the latest 1.x release.

## Reporting

Please do not publish an exploit, secret, or private document in a public issue.
Contact the repository owner privately and include:

- affected version or commit
- reproduction steps
- expected impact
- any suggested mitigation

## Deployment warning

The default project is a single-user local application. It does not ship with
authentication, malware scanning, tenant isolation, or an internet-facing rate
limit. Add these controls before using it as a shared service.

Never upload confidential material to a deployment you do not control. Ollama
keeps generation local by default, while selecting an OpenAI-compatible
provider sends prompts and retrieved context to that configured provider.
