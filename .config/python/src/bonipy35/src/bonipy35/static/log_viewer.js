"use strict";

class HighlightCheckbox extends HTMLElement {
  constructor() {
    super();
    const template = document.querySelector(
      "#template-highlight-checkbox",
    );
    const content = template.content.cloneNode(true);
    this.appendChild(content);
  }

  connectedCallback() {
    if (this.hasAttribute("type")) {
      const highlightType = this.getAttribute("type");

      const span = this.querySelector("span");
      span.textContent = highlightType;
      const spanClass = `highlight-${highlightType}`;
      span.classList.add(spanClass);

      const label = this.querySelector("label");
      label.setAttribute("class", "");
      const labelClass = `enable-${spanClass}`;
      label.classList.add(labelClass);

      const input = this.querySelector("input");
      input.value = highlightType;
      if (this.hasAttribute("checked")) {
        input.checked = true;
      }

      input.addEventListener("change", this.onChange);
      this.onChange({ target: input });
    }
  }

  onChange(e) {
    const logViewer = document.getElementById("log-viewer");
    const value = e.target.value;
    const labelClass = `enable-highlight-${value}`;
    if (e.target.checked) {
      logViewer.classList.add(labelClass);
    } else {
      logViewer.classList.remove(labelClass);
    }
  }
}

class LogViewer {
  constructor() {
    this.currentContent = "";
    this.currentHighlights = {};
    this.initializeElements();
    this.bindEvents();
    this.logStylesheet = new CSSStyleSheet();
    this.updateLogStylesheet([
      "all",
      "datetime",
      "error",
      "warning",
      "info",
      "debug",
      "stderr",
      "fatal",
    ]);
    document.adoptedStyleSheets.push(this.logStylesheet);
  }

  updateLogStylesheet(styleNames) {
    const myStyleNames = styleNames.slice();
    {
      const item = "all";
      const index = myStyleNames.indexOf(item);
      if (index > -1) {
        myStyleNames.splice(index, 1);
      }
      myStyleNames.splice(0, 0, item);
    }

    const logStylesheet = this.logStylesheet;
    for (const highlightType of myStyleNames) {
      const spanClass = `highlight-${highlightType}`;
      let styleString = `.enable-${spanClass} .line-${spanClass} {`;
      styleString += " display: unset";
      styleString += " }\n";
      logStylesheet.insertRule(styleString);
    }
  }

  initializeElements() {
    // Get DOM elements
    this.hamburger = document.getElementById("hamburger");
    this.sidebar = document.getElementById("sidebar");
    this.filePathInput = document.getElementById("file-path");
    this.loadFileButton = document.getElementById("load-file");
    this.logViewer = document.getElementById("log-viewer");
    this.statusBar = document.getElementById("status-bar");

    this.sidebar.classList.toggle("hidden");

    const highlightControls = document.getElementById(
      "highlight-controls",
    );
    const types = [
      "all",
      "datetime",
      "error",
      "warning",
      "info",
      "debug",
      "stderr",
      "fatal",
    ];
    for (let type of types) {
      const checkbox = document.createElement("highlight-checkbox");
      checkbox.setAttribute("type", type);
      if (type == "all") {
        checkbox.setAttribute("checked", true);
      }
      highlightControls.appendChild(checkbox);
    }
  }

  bindEvents() {
    // Hamburger menu toggle
    this.hamburger.addEventListener("click", () => {
      this.sidebar.classList.toggle("hidden");
    });

    // Load file button
    this.loadFileButton.addEventListener("click", () => {
      this.loadLogFile();
    });

    // Enter key on file path input
    this.filePathInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.loadLogFile();
      }
    });
  }

  async loadLogFile() {
    const filePath = this.filePathInput.value.trim();

    if (!filePath) {
      this.showStatus("Please enter a file path", "error");
      return;
    }

    this.showStatus("Loading file...", "info");
    this.logViewer.classList.add("loading");

    try {
      const response = await fetch("/api/log", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ path: filePath }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to load file");
      }

      this.currentContent = data.content;
      this.currentHighlights = data.highlights;

      this.displayLogContent();

      this.showStatus(
        `Loaded ${data.file_path} successfully`,
        "success",
      );
    } catch (error) {
      console.error("Error loading file:", error);
      this.showStatus(`Error: ${error.message}`, "error");
      this.logViewer.replaceChildren();
    } finally {
      this.logViewer.classList.remove("loading");
    }
  }

  displayLogContent() {
    if (!this.currentContent) {
      this.logViewer.replaceChildren();
      return;
    }

    // Create array of all highlights with their positions
    const allHighlights = [];

    Object.keys(this.currentHighlights).forEach((type) => {
      this.currentHighlights[type].forEach((highlight) => {
        allHighlights.push({
          ...highlight,
          type: type,
        });
      });
    });

    // Wrap every line with a span with class `highlight-all`.
    {
      let currentContent = this.currentContent;
      let start = 0;
      for (
        let end = currentContent.indexOf("\n", start) + 1;
        end > 0;
        start = end, end = currentContent.indexOf("\n", start) + 1
      ) {
        allHighlights.push({
          end,
          start,
          type: "all",
        });
      }
      let end = currentContent.length;
      if (start < end) {
        allHighlights.push({
          end: currentContent.length,
          start,
          type: "all",
        });
      }
    }

    // Sort highlights by start position.
    // If equal, take the longer span first.
    allHighlights.sort((a, b) =>
      a.start - b.start != 0 ? a.start - b.start : b.end - a.end,
    );

    const indexChanges = {};
    {
      const activeClasses = new Set();
      for (const { start, end, type } of allHighlights) {
        if (start == end) {
          continue;
        }

        if (!indexChanges[start])
          indexChanges[start] = {
            start: [],
            end: [],
          };
        indexChanges[start].start.push(type);

        if (!indexChanges[end])
          indexChanges[end] = {
            start: [],
            end: [],
          };
        indexChanges[end].end.push(type);
      }
    }

    const spanClasses = {};
    {
      const currentContent = this.currentContent;
      const contentLength = currentContent.length;

      const activeClasses = new Set();
      const lineClasses = new Set();
      let lineStartIndex = 0;
      let prevIndex = undefined;
      for (const [nextIndex, indexChange] of Object.entries(
        indexChanges,
      )) {
        if (
          nextIndex > 0 &&
          (nextIndex >= contentLength ||
            currentContent[nextIndex - 1] == "\n")
        ) {
          spanClasses[lineStartIndex].lineClasses =
            Array.from(lineClasses);
          lineClasses.clear();

          if (prevIndex !== undefined) {
            spanClasses[prevIndex].lineEnds = true;
          }

          lineStartIndex = nextIndex;
        }

        for (const type of indexChange.end) {
          activeClasses.delete(type);
        }
        for (const type of indexChange.start) {
          activeClasses.add(type);
        }

        for (const type of activeClasses) {
          lineClasses.add(type);
        }

        spanClasses[nextIndex] = {
          classes: Array.from(activeClasses),
        };

        if (prevIndex !== undefined) {
          spanClasses[prevIndex].end = nextIndex;
        }
        prevIndex = nextIndex;
      }
    }

    let result = "";
    {
      let currentContent = this.currentContent;
      for (const [nextIndex, thisSpanClasses] of Object.entries(
        spanClasses,
      )) {
        if (
          thisSpanClasses.lineClasses !== undefined &&
          thisSpanClasses.lineClasses.length > 0
        ) {
          let classString =
            thisSpanClasses.lineClasses.join(" line-highlight-");
          result += `<span class="line-highlight-${classString}">`;
        }

        if (thisSpanClasses.classes.length > 0) {
          let classString = thisSpanClasses.classes.join(" highlight-");
          result += `<span class="highlight-${classString}">`;
        }

        result += this.escapeHtml(
          this.currentContent.slice(nextIndex, thisSpanClasses.end),
        );

        if (thisSpanClasses.classes.length > 0) {
          result += "</span>";
        }

        if (thisSpanClasses.lineEnds) {
          result += "</span>";
        }
      }
    }

    this.logViewer.innerHTML = result;
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  showStatus(message, type = "info") {
    this.statusBar.textContent = message;
    this.statusBar.className = `status-bar ${type} show`;

    // Hide after 3 seconds
    setTimeout(() => {
      this.statusBar.classList.remove("show");
    }, 3000);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.logViewer = new LogViewer();
  customElements.define("highlight-checkbox", HighlightCheckbox);
});
