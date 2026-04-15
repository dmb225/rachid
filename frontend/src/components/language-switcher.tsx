"use client";

import { useLocale } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import { locales, type Locale, getLocaleLabel } from "@/i18n";

/**
 * Language switcher dropdown component.
 */
export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleChange = (newLocale: Locale) => {
    const segments = pathname.split("/");
    segments[1] = newLocale;
    router.push(segments.join("/"));
  };

  return (
    <div className="flex gap-1">
      {locales.map((loc) => (
        <button
          key={loc}
          onClick={() => handleChange(loc)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            locale === loc
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-label={getLocaleLabel(loc)}
          aria-pressed={locale === loc}
        >
          {loc.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

/**
 * Compact language switcher — minimal segmented control.
 */
export function LanguageSwitcherCompact() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleChange = (newLocale: Locale) => {
    const segments = pathname.split("/");
    segments[1] = newLocale;
    router.push(segments.join("/"));
  };

  return (
    <div className="border-border flex rounded-md border text-xs">
      {locales.map((loc, i) => (
        <button
          key={loc}
          onClick={() => handleChange(loc)}
          className={`px-2 py-1 font-medium transition-colors ${
            i > 0 ? "border-border border-l" : ""
          } ${
            locale === loc
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-label={getLocaleLabel(loc)}
        >
          {loc.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
