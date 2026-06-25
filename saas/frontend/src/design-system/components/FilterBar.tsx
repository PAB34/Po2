import type { ReactNode } from "react";
type FilterBarProps = { searchPlaceholder?: string; searchValue?: string; onSearchChange?: (value: string) => void; children?: ReactNode; };

export function FilterBar({ searchPlaceholder = "Rechercher", searchValue = "", onSearchChange, children }: FilterBarProps) {
  return <div className="po2-filter-bar"><label className="po2-filter-search"><span>⌕</span><input value={searchValue} placeholder={searchPlaceholder} onChange={(event) => onSearchChange?.(event.target.value)} /></label>{children}</div>;
}
