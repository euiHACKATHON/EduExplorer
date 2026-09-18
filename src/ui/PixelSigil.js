export function sigilHTML(level, className = "pixel-sigil") {
  const cells = level.sigil
    .join("")
    .split("")
    .map((cell) => `<i${cell === "1" ? ' class="lit"' : ""}></i>`)
    .join("");
  return `<span class="${className}" aria-label="${level.realm} emblem">${cells}</span>`;
}

export function drawPixelSigil(graphics, level, centerX, centerY, size = 7) {
  const width = level.sigil[0].length * size;
  const height = level.sigil.length * size;
  level.sigil.forEach((row, y) => {
    [...row].forEach((cell, x) => {
      if (cell === "1")
        graphics.fillRect(
          Math.round(centerX - width / 2 + x * size),
          Math.round(centerY - height / 2 + y * size),
          size,
          size,
        );
    });
  });
}
