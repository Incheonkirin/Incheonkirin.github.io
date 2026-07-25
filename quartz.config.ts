import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"

/**
 * Quartz 4 Configuration
 *
 * See https://quartz.jzhao.xyz/configuration for more information.
 */
const config: QuartzConfig = {
  configuration: {
    pageTitle: "Mingi Jeong",
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: {
      provider: "goatcounter",
      websiteId: "incheonkirin",
    },
    locale: "en-US",
    baseUrl: "incheonkirin.github.io",
    ignorePatterns: ["private", "templates", ".obsidian", "**/pulse-inbox/**"],
    defaultDateType: "modified",
    theme: {
      // toss.tech 톤 — Pretendard, 17px/1.7 본문, 토스 그레이 스케일 + 토스 블루.
      // 화면 폰트는 Head.tsx의 jsdelivr Pretendard + custom.scss 강제가 담당.
      // 여기 typography는 OG 이미지 렌더링(구글 폰트 필요)과 fallback용 Noto Sans KR.
      fontOrigin: "googleFonts",
      cdnCaching: true,
      typography: {
        header: "Noto Sans KR",
        body: "Noto Sans KR",
        code: "JetBrains Mono",
      },
      colors: {
        lightMode: {
          light: "#ffffff",        // white
          lightgray: "#e5e8eb",    // toss gray-200 (hairline)
          gray: "#8b95a1",         // toss gray-500 (meta)
          darkgray: "#333d4b",     // toss gray-800 (body)
          dark: "#191f28",         // toss gray-900 (ink)
          secondary: "#3182f6",    // toss blue
          tertiary: "#1b64da",     // toss blue-dark (hover)
          highlight: "rgba(49, 130, 246, 0.08)",
          textHighlight: "#fff8a3",
        },
        darkMode: {
          light: "#17171c",        // toss dark bg
          lightgray: "#2c2c35",
          gray: "#8b95a1",
          darkgray: "#d1d6db",
          dark: "#e5e8eb",
          secondary: "#4593fc",
          tertiary: "#7db2ff",
          highlight: "rgba(69, 147, 252, 0.12)",
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
        rssLimit: 20,
        includeEmptyFiles: false,
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
