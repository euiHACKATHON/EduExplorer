export const THEMES = {
  amber: {
    accent: "#f0bf78",
    accentStrong: "#d99a4e",
    surface: "#403526",
    border: "#806945",
    text: "#f6e5c6",
  },
  teal: {
    accent: "#87c5bd",
    accentStrong: "#4aa99f",
    surface: "#233b3a",
    border: "#4a756e",
    text: "#d4f0eb",
  },
  violet: {
    accent: "#c1a7dc",
    accentStrong: "#9d7bc4",
    surface: "#382d45",
    border: "#6e5980",
    text: "#eadcf8",
  },
};

export function applyTheme(theme = "amber") {
  const selected = THEMES[theme] ? theme : "amber";
  document.documentElement.dataset.theme = selected;
  return selected;
}