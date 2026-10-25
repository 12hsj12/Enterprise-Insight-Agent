/** @type {import('@docusaurus/types').DocusaurusConfig} */
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const isProductionBuild = process.env.NODE_ENV === 'production';
const configuredSiteUrl = process.env.DOCS_SITE_URL;
const configuredBaseUrl = process.env.DOCS_BASE_URL;

if (isProductionBuild && (!configuredSiteUrl || !configuredBaseUrl)) {
  throw new Error(
    'Set DOCS_SITE_URL and DOCS_BASE_URL to the confirmed documentation host and path before building for production.',
  );
}

export default {
  title: 'Enterprise Insight Agent',
  tagline: 'Evidence-grounded research for enterprise decisions',
  url: configuredSiteUrl || 'http://localhost:3000',
  baseUrl: configuredBaseUrl || '/',
  onBrokenLinks: 'ignore',
  //deploymentBranch: 'master',
  organizationName: '12hsj12',
  trailingSlash: false,
  projectName: 'Enterprise-Insight-Agent',
  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },
  themes: ['@docusaurus/theme-mermaid'],
  themeConfig: {
    navbar: {
      title: 'Enterprise Insight Agent',
      items: [
        {
          type: 'doc',
          docId: 'welcome',
          position: 'left',
          label: 'Docs',
        },

        {
          href: 'https://github.com/12hsj12/Enterprise-Insight-Agent',
          position: 'right',
          label: 'GitHub',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Project',
          items: [
            {
              label: 'GitHub repository',
              href: 'https://github.com/12hsj12/Enterprise-Insight-Agent',
            },
            {
              label: 'Apache License 2.0',
              href: 'https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/LICENSE',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Enterprise Insight Agent.`,
    },
  },
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl:
            'https://github.com/12hsj12/Enterprise-Insight-Agent/tree/main/docs',
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
        },
        blog: {
          onUntruncatedBlogPosts: 'ignore',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
  stylesheets: [
    {
        href: "https://cdn.jsdelivr.net/npm/katex@0.13.11/dist/katex.min.css",
        integrity: "sha384-Um5gpz1odJg5Z4HAmzPtgZKdTBHZdw8S29IecapCSB31ligYPhHQZMIlWLYQGVoc",
        crossorigin: "anonymous",
    },
  ],

  plugins: [
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        hashed: true,
        blogDir:"./blog/"
      },
    ],
  ],
};
