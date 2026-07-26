import { FullSlug, resolveRelative } from "../util/path"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

const languageLabels: Record<string, string> = {
  en: "EN",
  ko: "KO",
}

const LanguageSwitcher: QuartzComponent = ({ fileData }: QuartzComponentProps) => {
  const translations = fileData.frontmatter?.translations as Record<string, string> | undefined
  const languages = ["en", "ko"].filter((lang) => translations?.[lang])

  if (!translations || languages.length < 2) {
    return null
  }

  const currentLanguage = fileData.frontmatter?.lang ?? "en"

  return (
    <nav class="language-switcher" aria-label="Post language">
      {languages.map((lang) =>
        lang === currentLanguage ? (
          <span class="language-option active" aria-current="page">
            {languageLabels[lang] ?? lang.toUpperCase()}
          </span>
        ) : (
          <a
            class="language-option internal"
            href={resolveRelative(fileData.slug!, translations[lang] as FullSlug)}
            hrefLang={lang}
          >
            {languageLabels[lang] ?? lang.toUpperCase()}
          </a>
        ),
      )}
    </nav>
  )
}

LanguageSwitcher.css = `
.language-switcher {
  display: flex;
  width: fit-content;
  gap: 0.25rem;
  margin-top: 0.85rem;
  font-size: 0.78rem;
  font-weight: 650;
  letter-spacing: 0.03em;
}

.language-switcher .language-option,
.language-switcher a.language-option.internal {
  min-width: 2.35rem;
  padding: 0.25rem 0.55rem;
  border: 1px solid var(--lightgray);
  border-radius: 0.4rem;
  color: var(--gray);
  background: transparent;
  text-align: center;
  line-height: 1.35;
}

.language-switcher a.language-option.internal:hover {
  color: var(--dark);
  border-color: var(--gray);
}

.language-switcher .language-option.active {
  color: var(--light);
  border-color: var(--dark);
  background: var(--dark);
}
`

export default (() => LanguageSwitcher) satisfies QuartzComponentConstructor
