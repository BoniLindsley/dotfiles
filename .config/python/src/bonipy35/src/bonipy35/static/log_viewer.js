"use strict";

function debounce(fn, delay = 300) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), delay);
  };
}

function updateSuggestions(path) {
  fetch(`/suggest?path=${encodeURIComponent(path)}`)
    .then((response) => response.json())
    .then((results) => {
      const parent = path.includes("/")
        ? path.substring(0, path.lastIndexOf("/") + 1)
        : "";
      const suggestions = document.getElementById("suggestions");
      suggestions.innerHTML = results
        .map((item) => `<option value="${parent}${item}">`)
        .join("");
    });
}

const filepath = document.getElementById("filepath");
filepath.addEventListener("input", (e) => {
  const path = e.target.value;
  debounce(updateSuggestions)(path);
});

function loadFile(path) {
  const contentDiv = document.getElementById("content");
  const filepathErrorDiv = document.getElementById("filepath-error");
  const filterErrorDiv = document.getElementById("filter-error");
  fetch(`/file?path=${encodeURIComponent(path)}`)
    .then((response) => {
      if (!response.ok) {
        return response.text().then((text) => {
          filepathErrorDiv.textContent = text;
          return "";
        });
      }
      filepathErrorDiv.textContent = "";
      return response.text();
    })
    .then((text) => {
      contentDiv.textContent = text;
      applyFilter();
      filterErrorDiv.textContent = "";
    })
    .catch((err) => {
      contentDiv.textContent = "";
      filterErrorDiv.textContent = `Error loading file: ${err}`;
    });
}

const filepathButton = document.getElementById("filepath-button");
filepathButton.addEventListener("click", () => {
  const path = filepath.value;
  loadFile(path);
});

const filterText = document.getElementById("filter-text");
function applyFilter() {
  const filter = filterText.value;
  const contentDiv = document.getElementById("content");

  try {
    const regex = new RegExp(filter, "i");
    contentDiv.innerHTML = contentDiv.textContent
      .split("\n")
      .map((line) =>
        regex.test(line) ? line : `<span class="dimmed">${line}</span>`,
      )
      .join("\n");
  } catch (e) {
    const filterErrorDiv = document.getElementById("filter-error");
    filterErrorDiv.textContent = `Invalid regex: ${e}`;
  }
}

filterText.addEventListener("input", (e) => {
  const path = e.target.value;
  debounce(applyFilter)();
});
