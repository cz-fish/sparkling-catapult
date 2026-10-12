"use strict";

for (const list of document.querySelectorAll("[data-post-list]")) {
  const cards = Array.from(list.querySelectorAll(".post"));
  const search = document.querySelector(`[data-search-for="${list.id}"]`);
  const order = document.querySelector(`[data-order-for="${list.id}"]`);
  const previous = document.querySelector(`[data-previous-for="${list.id}"]`);
  const next = document.querySelector(`[data-next-for="${list.id}"]`);
  const pageStatus = document.querySelector(`[data-page-for="${list.id}"]`);
  const emptyState = document.querySelector(`[data-empty-for="${list.id}"]`);
  const pageSize = Number(list.dataset.pageSize);
  let currentPage = 1;

  function render() {
    const query = search.value.trim().toLocaleLowerCase();
    const visibleCards = cards.filter((card) =>
      card.dataset.searchText.toLocaleLowerCase().includes(query),
    );

    if (order.value === "newest") {
      visibleCards.reverse();
    }

    const pageCount = Math.max(1, Math.ceil(visibleCards.length / pageSize));
    currentPage = Math.min(currentPage, pageCount);
    const start = (currentPage - 1) * pageSize;
    const pageCards = new Set(visibleCards.slice(start, start + pageSize));

    for (const card of cards) {
      card.hidden = !pageCards.has(card);
      list.append(card);
    }

    emptyState.hidden = visibleCards.length !== 0;
    pageStatus.textContent = `Page ${currentPage} of ${pageCount}`;
    previous.disabled = currentPage === 1;
    next.disabled = currentPage === pageCount;
  }

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
