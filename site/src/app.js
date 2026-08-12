(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-theme-toggle]");

  try {
    const stored = localStorage.getItem("sssp-theme");
    if (stored === "light" || stored === "dark") {
      root.dataset.theme = stored;
    }
  } catch (_) {
    // Storage can be unavailable in privacy-restricted contexts.
  }

  themeButton?.addEventListener("click", () => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const current = root.dataset.theme || (prefersDark ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try {
      localStorage.setItem("sssp-theme", next);
    } catch (_) {
      // Theme switching still works for this page view without storage.
    }
  });

  const tabs = [...document.querySelectorAll("[data-lens]")];
  const selectTab = (tab, moveFocus = false) => {
    const target = tab.dataset.lens;
    tabs.forEach((candidate) => {
      const selected = candidate === tab;
      candidate.setAttribute("aria-selected", String(selected));
      candidate.tabIndex = selected ? 0 : -1;
      const panel = document.getElementById(`lens-${candidate.dataset.lens}`);
      if (panel) panel.hidden = !selected;
    });
    if (moveFocus) tab.focus();
    history.replaceState(null, "", `#protocol-${target}`);
  };

  tabs.forEach((tab, index) => {
    tab.tabIndex = tab.getAttribute("aria-selected") === "true" ? 0 : -1;
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      selectTab(tabs[next], true);
    });
  });

  const hashLens = location.hash.match(/^#protocol-(canonical|export|audit)$/)?.[1];
  if (hashLens) {
    const initial = tabs.find((tab) => tab.dataset.lens === hashLens);
    if (initial) selectTab(initial);
  }

  const copyButton = document.querySelector("[data-copy-command]");
  copyButton?.addEventListener("click", async () => {
    const code = copyButton.closest(".terminal")?.querySelector("code")?.textContent;
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
      const original = copyButton.dataset.copyLabel || copyButton.textContent;
      copyButton.textContent = copyButton.dataset.copiedLabel || "Copied";
      window.setTimeout(() => {
        copyButton.textContent = original;
      }, 1600);
    } catch (_) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(copyButton.closest(".terminal").querySelector("code"));
      selection.removeAllRanges();
      selection.addRange(range);
    }
  });
})();
