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

      input.addEventListener("change", (e) => {
        const logViewer = document.getElementById("log-viewer");
        const value = e.target.Value;
        if (e.target.checked) {
          logViewer.classList.add(labelClass);
        } else {
          logViewer.classList.remove(labelClass);
        }
      });
    }
  }
}

class LogViewer {
  constructor() {
    this.currentContent = "";
    this.currentHighlights = {};
    this.initializeElements();
    this.bindEvents();
  }

  createLogStylesheet() {
    const logStylesheet = new CSSStyleSheet();
    const styles = {
      datetime: {
        "background-color": "rgba(78, 201, 176, 0.2)",
        color: "#4ec9b0",
      },
      error: {
        "background-color": "rgba(244, 71, 71, 0.2)",
        color: "#f44747",
      },
      warning: {
        "background-color": "rgba(255, 204, 2, 0.2)",
        color: "#ffcc02",
      },
      info: {
        "background-color": "rgba(55, 148, 255, 0.2)",
        color: "#3794ff",
      },
      debug: {
        "background-color": "rgba(181, 206, 168, 0.2)",
        color: "#b5cea8",
      },
      stderr: {
        "background-color": "rgba(255, 107, 107, 0.2)",
        color: "#ff6b6b",
      },
      fatal: {
        "background-color": "rgba(255, 0, 102, 0.2)",
        color: "#ff0066",
      },
    };
    for (const [highlightType, ruleProperties] of Object.entries(
      styles,
    )) {
      const spanClass = `highlight-${highlightType}`;
      let styleString = `.enable-${spanClass} .${spanClass} {`;
      for (const [name, value] of Object.entries(ruleProperties)) {
        styleString += ` ${name}: ${value};`;
      }
      styleString += " }";
      console.log(styleString);
      logStylesheet.insertRule(styleString);
    }
    document.adoptedStyleSheets.push(this.createLogStylesheet());
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

    // Sort highlights by start position
    allHighlights.sort((a, b) => a.start - b.start);

    // Apply highlights to content
    let result = "";
    let lastIndex = 0;

    allHighlights.forEach((highlight) => {
      // Add content before highlight
      result += this.escapeHtml(
        this.currentContent.slice(lastIndex, highlight.start),
      );

      // Add highlighted content
      result += `<span class="highlight-${highlight.type}">`;
      result += this.escapeHtml(
        this.currentContent.slice(highlight.start, highlight.end),
      );
      result += "</span>";

      lastIndex = highlight.end;
    });

    // Add remaining content
    result += this.escapeHtml(this.currentContent.slice(lastIndex));

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
