/* TripMate AI interactions + formatted itinerary renderer */
(() => {
  const form = document.getElementById("trip-form");
  const promptInput = document.getElementById("trip-prompt");
  const charCount = document.getElementById("char-count");
  const generateButton = document.getElementById("generate-button");
  const output = document.getElementById("plan-output");
  const chips = document.querySelectorAll("[data-prompt]");
  const API_ENDPOINT = "/api/travel"; // Setup to LangGraph/API endpoint.

  const updateCount = () => {
    const n = promptInput.value.length;
    charCount.textContent = `${n} character${n === 1 ? "" : "s"}`;
  };
  const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
  const inlineFormat = s => escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");

  function renderItinerary(itinerary) {
    if (!itinerary) {
      return `<p class="empty-result">No itinerary details available.</p>`;
    }

    // Handle arrays and objects using the existing renderer
    if (typeof itinerary !== "string") {
      return renderResultsList(itinerary, "itinerary");
    }

    const normalized = itinerary
      .replace(/\\n/g, "\n")
      .replace(/\r\n?/g, "\n")
      .trim();

    if (!normalized) {
      return `<p class="empty-result">No itinerary details available.</p>`;
    }

    const lines = normalized.split("\n");
    const html = [];
    let listType = null;
    let paragraph = [];

    function closeList() {
      if (listType) {
        html.push(`</${listType}>`);
        listType = null;
      }
    }

    function flushParagraph() {
      if (paragraph.length) {
        html.push(`<p>${inlineFormat(paragraph.join(" "))}</p>`);
        paragraph = [];
      }
    }

    for (const rawLine of lines) {
      const line = rawLine.trim();

      if (!line) {
        flushParagraph();
        closeList();
        continue;
      }

      // Markdown headings: # Heading, ## Heading, etc.
      const heading = line.match(/^(#{1,6})\s+(.+)$/);

      if (heading) {
        flushParagraph();
        closeList();

        const level = Math.min(heading[1].length + 1, 6);
        html.push(`<h${level}>${inlineFormat(heading[2])}</h${level}>`);
        continue;
      }

      // Markdown bullet or numbered list items
      const bullet = line.match(/^[-*•]\s+(.+)$/);
      const numbered = line.match(/^\d+[.)]\s+(.+)$/);

      if (bullet || numbered) {
        flushParagraph();

        const nextType = numbered ? "ol" : "ul";

        if (listType !== nextType) {
          closeList();
          html.push(`<${nextType} class="itinerary-list">`);
          listType = nextType;
        }

        const content = (bullet || numbered)[1];
        html.push(`<li>${inlineFormat(content)}</li>`);
        continue;
      }

      flushParagraph();
      closeList();
      paragraph.push(line);
    }

    flushParagraph();
    closeList();

    return `<div class="itinerary-body">${html.join("\n")}</div>`;
  }

  function renderResultsList(data, type = "result") {
    if (data == null || data === "") {
      return `<p class="empty-result">No ${escapeHtml(type)} information available.</p>`;
    }

    // Handle arrays of results
    if (Array.isArray(data)) {
      if (data.length === 0) {
        return `<p class="empty-result">No ${escapeHtml(type)} results found.</p>`;
      }

      return `
      <ul class="result-list">
        ${data.map(item => `
          <li>${renderResultItem(item)}</li>
        `).join("")}
      </ul>
    `;
    }

    // Handle objects
    if (typeof data === "object") {
      return `
      <div class="result-details">
        ${Object.entries(data).map(([key, value]) => `
          <div class="result-row">
            <strong>${escapeHtml(formatLabel(key))}:</strong>
            <div>${renderResultItem(value)}</div>
          </div>
        `).join("")}
      </div>
    `;
    }

    // Handle plain text or stringified API results
    return `<div class="result-text">${renderPlainText(data)}</div>`;
  }

  function renderResultItem(value) {
    if (value == null || value === "") {
      return `<span>Not available</span>`;
    }

    if (Array.isArray(value)) {
      return `
      <ul>
        ${value.map(item => `<li>${renderResultItem(item)}</li>`).join("")}
      </ul>
    `;
    }

    if (typeof value === "object") {
      return `
      <div class="nested-result">
        ${Object.entries(value).map(([key, item]) => `
          <p>
            <strong>${escapeHtml(formatLabel(key))}:</strong>
            ${renderResultItem(item)}
          </p>
        `).join("")}
      </div>
    `;
    }

    return renderPlainText(value);
  }

  function renderPlainText(value) {
    return escapeHtml(String(value))
      .replace(/\r\n?/g, "\n")
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/(https?:\/\/[^\s<]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  }

  function renderTripResults(data) {
    const flights = data.flight_results;
    const hotels = data.hotel_results;
    const itinerary = data.itinerary;
    console.log(`Rendering trip results with flights:===+++++++++++++++++++>>>>>>>>>. ${JSON.stringify(flights)}, hotels: ${JSON.stringify(hotels)}, itinerary: ${itinerary}`);
    return `
    <article class="itinerary-document">
      <div class="document-topline">
        <span class="document-badge">TRIPMATE AI</span>
        <span class="document-caption">
          YOUR PERSONALIZED ITINERARY
        </span>
      </div>

      <div class="itinerary-content">
        <h1>${escapeHtml(data.user_query || "Your Trip Plan")}</h1>

        <h2>1. Flight Information</h2>
        ${renderResultsList(flights, "flight")}

        <h2>2. Hotel Suggestions</h2>
        ${renderResultsList(hotels, "hotel")}

        <h2>3. Complete Travel Itinerary</h2>
        ${renderItinerary(itinerary)}
      </div>

      <div class="document-footer">
        Please verify travel details, availability and prices before booking.
      </div>
    </article>
  `;
  }

  function formatLabel(key) {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  promptInput.addEventListener("input", updateCount);
  chips.forEach(chip => chip.addEventListener("click", () => {
    promptInput.value = chip.dataset.prompt || ""; updateCount(); promptInput.focus();
  }));
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (generateButton.disabled) return;
    const message = promptInput.value.trim();
    if (!message) { promptInput.focus(); return; }
    if (!API_ENDPOINT) {
      output.innerHTML = renderTripResults(
        "Your trip request is ready.\n\nSet API_ENDPOINT in scripts.js to your existing LangGraph backend endpoint to display the complete generated itinerary here. The renderer formats the response into a report with headings, paragraphs and bullet lists."
      );
      output.scrollIntoView({ behavior: "smooth", block: "start" }); return;
    }
    const original = generateButton.innerHTML;
    generateButton.disabled = true;
    generateButton.innerHTML = '<span class="button-copy"><span>Building your plan…</span><small>Agents are working together</small></span><span class="button-arrow">◌</span>';
    output.innerHTML = '<div class="plan-loading"><span class="loading-orb"></span><div><strong>Planning your next adventure</strong><p>Your AI travel crew is gathering the details…</p></div></div>';
    output.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message })
      });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const responseData = await response.json();
      const plan = responseData.answer ?? responseData;
      console.log("Trip plan:", plan);
      output.innerHTML = renderTripResults(plan);
    } catch (error) {
      console.error("Travel API or rendering error:", error);

      output.innerHTML = `
    <article class="itinerary-document">
      <div class="itinerary-content">
        <h2>Unable to generate your trip</h2>
        <p>${escapeHtml(error.message)}</p>
        <p>Please check your API endpoint and response format.</p>
      </div>
    </article>
  `;
    } finally {
      generateButton.disabled = false;
      generateButton.innerHTML = original;
    }
  });
  updateCount();
})();
