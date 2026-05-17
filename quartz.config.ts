import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"

/**
 * Quartz 4 Configuration
 *
 * See https://quartz.jzhao.xyz/configuration for more information.
 */
const config: QuartzConfig = {
  configuration: {
    pageTitle: "Matthew Jeong",
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: {
      provider: "plausible",
    },
    locale: "ko-KR",
    baseUrl: "incheonkirin.github.io",
    ignorePatterns: ["private", "templates", ".obsidian"],
    defaultDateType: "modified",
    theme: {
      // Karpathy.github.io 톤 — austere minimal, serif headers,
      // near-black on white, classic blue links. 한국어는 Pretendard fallback.
      fontOrigin: "googleFonts",
      cdnCaching: true,
      typography: {
        header: "EB Garamond",
        body: "Inter",
        code: "JetBrains Mono",
      },
      colors: {
        lightMode: {
          light: "#ffffff",        // pure white
          lightgray: "#e8e8e8",    // hairline
          gray: "#888888",         // muted
          darkgray: "#333333",     // body
          dark: "#1a1a1a",         // ink
          secondary: "#0645ad",    // classic blue link (wikipedia style)
          tertiary: "#0645ad",
          highlight: "rgba(6, 69, 173, 0.06)",
          textHighlight: "#fff8a3",
        },
        darkMode: {
          light: "#1a1a1a",
          lightgray: "#2c2c2c",
          gray: "#888888",
          darkgray: "#cccccc",
          dark: "#f0f0f0",
          secondary: "#79b8ff",    // blue lighter for dark bg
          tertiary: "#79b8ff",
          highlight: "rgba(121, 184, 255, 0.10)",
          textHighlight: "#fff8a355",
        },
      },
    },
  },
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      Plugin.CreatedModifiedDate({
        priority: ["frontmatter", "git", "filesystem"],
      }),
      Plugin.SyntaxHighlighting({
        theme: {
          light: "github-light",
          dark: "github-dark",
        },
        keepBackground: false,
      }),
      Plugin.ObsidianFlavoredMarkdown({ enableInHtmlEmbed: false }),
      Plugin.GitHubFlavoredMarkdown(),
      Plugin.TableOfContents(),
      Plugin.CrawlLinks({ markdownLinkResolution: "shortest" }),
      Plugin.Description(),
      Plugin.Latex({ renderEngine: "katex" }),
    ],
    filters: [Plugin.RemoveDrafts()],
    emitters: [
      Plugin.AliasRedirects(),
      Plugin.ComponentResources(),
      Plugin.ContentPage(),
      Plugin.FolderPage(),
      Plugin.TagPage(),
      Plugin.ContentIndex({
        enableSiteMap: true,
        enableRSS: true,
      }),
      Plugin.Assets(),
      Plugin.Static(),
      Plugin.Favicon(),
      Plugin.NotFoundPage(),
      // Comment out CustomOgImages to speed up build time
      Plugin.CustomOgImages(),
    ],
  },
}

export default config
