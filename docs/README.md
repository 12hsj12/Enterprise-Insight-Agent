# Enterprise Insight Agent documentation site

The documentation site is built with Docusaurus 3.10.2. Start with [`docs/docs/welcome.md`](docs/welcome.md), then use the sidebar's Enterprise Insight Agent section for the product guide. The separately labeled GPT Researcher reference sections retain upstream material and are not the current product overview.

## Local development

Use Node.js 20.x or 22.x and later releases with npm, then from this directory. The pinned documentation build security updates require Node.js 20 or newer; Node.js 21 is outside the dependency engine ranges:

```console
npm install
npm run start
```

Build locally with a local-only canonical URL. In PowerShell:

```console
$env:DOCS_SITE_URL = 'http://localhost:3000'
$env:DOCS_BASE_URL = '/'
npm run build
```

In Bash:

```console
DOCS_SITE_URL=http://localhost:3000 DOCS_BASE_URL=/ npm run build
```

For a production build, set `DOCS_SITE_URL` and `DOCS_BASE_URL` to the confirmed documentation host and path. The repository has no documentation deployment workflow or public domain configured. Repository content and edit links point to [12hsj12/Enterprise-Insight-Agent](https://github.com/12hsj12/Enterprise-Insight-Agent).
