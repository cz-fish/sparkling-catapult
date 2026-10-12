"use strict";

for (const list of document.querySelectorAll("[data-post-list]")) {
  const cards = Array.from(list.querySelectorAll(".post"));
  const search = document.querySelector(`[data-search-for="${list.id}"]`);
  const order = document.querySelector(`[data-order-for="${list.id}"]`);
  const previous = document.querySelector(`[data-previous-for="${list.id}"]`);
  const next = document.querySelector(`[data-next-for="${list.id}"]`);
  const pageStatus = document.querySelector(`[data-page-for="${list.id}"]`);
  const emptyState = document.querySelector(`[data-empty-for="${list.id}"]`);
  const viewer = document.querySelector(".post-viewer");
  const viewerImage = viewer.querySelector("[data-viewer-image]");
  const viewerTitle = viewer.querySelector("[data-viewer-title]");
  const viewerMeta = viewer.querySelector("[data-viewer-meta]");
  const viewerText = viewer.querySelector("[data-viewer-text]");
  const viewerPrevious = viewer.querySelector("[data-viewer-previous]");
  const viewerNext = viewer.querySelector("[data-viewer-next]");
  const viewerClose = viewer.querySelector("[data-viewer-close]");
  const pageSize = Number(list.dataset.pageSize);
  let currentPage = 1;
  let orderedCards = [];
  let selectedCard = null;

  function updateViewer() {
    if (!selectedCard) {
      return;
    }

    const selectedIndex = orderedCards.indexOf(selectedCard);
    if (selectedIndex === -1) {
      selectedCard = null;
      viewer.close();
      return;
    }

    const image = selectedCard.querySelector("img");
    viewerImage.src = image.src;
    viewerImage.alt = image.alt;
    viewerTitle.textContent = selectedCard.querySelector("h2").textContent;
    viewerMeta.replaceChildren(selectedCard.querySelector(".post-meta").cloneNode(true));
    const caption = selectedCard.querySelector(":scope > p:not(.post-meta)");
    viewerText.replaceChildren();
    if (caption) {
      viewerText.append(caption.cloneNode(true));
    }
    viewerPrevious.disabled = selectedIndex === 0;
    viewerNext.disabled = selectedIndex === orderedCards.length - 1;
  }

  function openViewer(card) {
    selectedCard = card;
    updateViewer();
    if (!viewer.open) {
      viewer.showModal();
    }
  }

  function navigateViewer(direction) {
    const selectedIndex = orderedCards.indexOf(selectedCard);
    const target = orderedCards[selectedIndex + direction];
    if (!target) {
      return;
    }
    currentPage = Math.floor(orderedCards.indexOf(target) / pageSize) + 1;
    render();
    openViewer(target);
  }

  function render() {
    const query = search.value.trim().toLocaleLowerCase();
    orderedCards = cards.filter((card) =>
      card.dataset.searchText.toLocaleLowerCase().includes(query),
    );

    if (order.value === "newest") {
      orderedCards.reverse();
    }

    const pageCount = Math.max(1, Math.ceil(orderedCards.length / pageSize));
    currentPage = Math.min(currentPage, pageCount);
    const start = (currentPage - 1) * pageSize;
    const pageCards = new Set(orderedCards.slice(start, start + pageSize));

    for (const card of cards) {
      card.hidden = !pageCards.has(card);
    }
    for (const card of orderedCards.slice(start, start + pageSize)) {
      list.append(card);
    }

    emptyState.hidden = orderedCards.length !== 0;
    pageStatus.textContent = `Page ${currentPage} of ${pageCount}`;
    previous.disabled = currentPage === 1;
    next.disabled = currentPage === pageCount;
    if (viewer.open) {
      updateViewer();
    }
  }

  list.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      return;
    }
    const card = event.target.closest(".post");
    if (card) {
      openViewer(card);
    }
  });
  list.addEventListener("keydown", (event) => {
    if (
      (event.key === "Enter" || event.key === " ") &&
      event.target.matches(".post")
    ) {
      event.preventDefault();
      openViewer(event.target);
    }
  });
  viewerPrevious.addEventListener("click", () => navigateViewer(-1));
  viewerNext.addEventListener("click", () => navigateViewer(1));
  viewerClose.addEventListener("click", () => viewer.close());
  viewer.addEventListener("click", (event) => {
    if (event.target === viewer) {
      viewer.close();
    }
  });

  search.addEventListener("input", () => {
    currentPage = 1;
    render();
  });
  order.addEventListener("change", () => {
    currentPage = 1;
    render();
  });
  previous.addEventListener("click", () => {
    currentPage -= 1;
    render();
  });
  next.addEventListener("click", () => {
    currentPage += 1;
    render();
  });

  render();
}
