import { FullSlug, resolveRelative } from "../util/path"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

const SiteNav: QuartzComponent = ({ fileData }: QuartzComponentProps) => {
  const aboutHref = resolveRelative(fileData.slug!, "about" as FullSlug)

  return (
    <nav class="site-nav" aria-label="Primary navigation">
      <a href={aboutHref} class="internal">
        Profile
      </a>
      <a href="https://github.com/incheonkirin">GitHub</a>
      <a href="https://www.linkedin.com/in/mingi-jeong-8a9210180/">LinkedIn</a>
    </nav>
  )
}

SiteNav.css = `
.site-nav {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.45rem;
  font-size: 0.95rem;
}

.site-nav a,
.site-nav a.internal {
  padding: 0;
  background: transparent;
  font-weight: 500;
}

@media all and (max-width: 800px) {
  .site-nav {
    margin-left: auto;
    flex-direction: row;
    gap: 1rem;
    align-items: center;
  }
}
`

export default (() => SiteNav) satisfies QuartzComponentConstructor
