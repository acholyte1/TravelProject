(function () {
    const main = document.querySelector("main[data-api-url]");
    const apiUrl = main.dataset.apiUrl;
    const searchInput = document.getElementById("travel-search");
    const clearSearch = document.getElementById("clear-search");
    const quickTags = document.getElementById("quick-tags");
    const filterForm = document.getElementById("travel-filter-form");
    const kindButtons = Array.from(document.querySelectorAll("[data-kind]"));
    const regionFilter = document.getElementById("region-filter");
    const statusFilter = document.getElementById("status-filter");
    const sortFilter = document.getElementById("sort-filter");
    const resetButton = document.getElementById("reset-filters");
    const recordList = document.getElementById("record-list");
    const detailCard = document.getElementById("detail-card");
    const errorBox = document.getElementById("travel-error");
    const resultCount = document.getElementById("result-count");
    const countryCount = document.getElementById("country-count");
    const locationCount = document.getElementById("location-count");
    const regionCount = document.getElementById("region-count");

    const state = {
        kind: "all",
        selectedKey: null,
        allItems: [],
        items: [],
        debounceId: null,
    };

    const statusLabel = {
        TRIP: "다녀옴",
        STAY: "머묾",
        WANT: "가고 싶음",
    };

    const kindLabel = {
        country: "국가",
        location: "도시",
    };

    function valueOrDash(value) {
        return value === null || value === undefined || value === "" ? "-" : String(value);
    }

    function makeRecordKey(item) {
        return `${item.kind}:${item.id}`;
    }

    function statusClass(status) {
        return status ? `status-${String(status).toLowerCase()}` : "status-empty";
    }

    function clearNode(node) {
        while (node.firstChild) {
            node.removeChild(node.firstChild);
        }
    }

    function appendText(parent, tagName, text, className) {
        const element = document.createElement(tagName);
        if (className) {
            element.className = className;
        }
        element.textContent = text;
        parent.appendChild(element);
        return element;
    }

    function buildParams(includeFilters) {
        const params = new URLSearchParams();
        const query = searchInput.value.trim();

        if (query) {
            params.set("q", query);
        }

        if (includeFilters) {
            if (state.kind !== "all") {
                params.set("kind", state.kind);
            }
            if (regionFilter.value) {
                params.set("region", regionFilter.value);
            }
            if (statusFilter.value) {
                params.set("status", statusFilter.value);
            }
            if (sortFilter.value) {
                params.set("sort", sortFilter.value);
            }
            if (sortFilter.value === "visit_count") {
                params.set("direction", "desc");
            }
        }

        return params;
    }

    async function fetchTravelRecords(includeFilters) {
        const params = buildParams(includeFilters);
        const url = params.toString() ? `${apiUrl}?${params.toString()}` : apiUrl;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error("검색 요청에 실패했습니다.");
        }

        return response.json();
    }

    function updateHeroStats(items) {
        const countries = items.filter((item) => item.kind === "country").length;
        const locations = items.filter((item) => item.kind === "location").length;
        const regions = new Set(items.map((item) => item.region_name).filter(Boolean)).size;

        countryCount.textContent = countries;
        locationCount.textContent = locations;
        regionCount.textContent = regions;
    }

    function populateRegionFilter(items) {
        const currentValue = regionFilter.value;
        const regions = Array.from(new Set(items.map((item) => item.region_name).filter(Boolean))).sort((a, b) => a.localeCompare(b, "ko"));

        clearNode(regionFilter);
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "전체 대륙";
        regionFilter.appendChild(defaultOption);

        for (const region of regions) {
            const option = document.createElement("option");
            option.value = region;
            option.textContent = region;
            regionFilter.appendChild(option);
        }

        if (regions.includes(currentValue)) {
            regionFilter.value = currentValue;
        }
    }

    function populateQuickTags(items) {
        const existingButtons = quickTags.querySelectorAll("button");
        existingButtons.forEach((button) => button.remove());

        const tags = items
            .filter((item) => item.kind === "country")
            .map((item) => item.name)
            .filter(Boolean)
            .slice(0, 3);

        for (const tag of tags) {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = `#${tag}`;
            button.addEventListener("click", () => {
                searchInput.value = tag;
                clearSearch.hidden = false;
                loadResults();
            });
            quickTags.appendChild(button);
        }
    }

    function renderEmptyState() {
        clearNode(recordList);
        const empty = document.createElement("div");
        empty.className = "empty-state";
        appendText(empty, "strong", "일치하는 기록이 없습니다.");
        appendText(empty, "p", "검색어를 줄이거나 필터를 초기화해 보세요.");
        const button = appendText(empty, "button", "전체 기록 보기");
        button.type = "button";
        button.addEventListener("click", resetFilters);
        recordList.appendChild(empty);
    }

    function renderDetail(item) {
        clearNode(detailCard);

        if (!item) {
            appendText(detailCard, "p", "왼쪽에서 기록을 선택하세요.");
            return;
        }

        const top = document.createElement("div");
        top.className = "detail-top";
        appendText(top, "span", kindLabel[item.kind] || valueOrDash(item.kind), "detail-kind");
        appendText(top, "span", statusLabel[item.visit_status] || valueOrDash(item.visit_status), `status ${statusClass(item.visit_status)}`);
        detailCard.appendChild(top);

        appendText(detailCard, "p", `${kindLabel[item.kind] || valueOrDash(item.kind)} 상세`, "detail-type");
        appendText(detailCard, "h3", valueOrDash(item.name));
        appendText(detailCard, "p", item.kind === "location" ? valueOrDash(item.country_name) : "Country record", "detail-local");
        appendText(detailCard, "p", "기존 MySQL 데이터에서 읽어 온 조회 전용 기록입니다.", "detail-note");

        const definitionList = document.createElement("dl");
        const details = [
            ["대륙", valueOrDash(item.region_name)],
            ["소속 국가", valueOrDash(item.country_name)],
            ["방문 횟수", Number(item.visit_count || 0) ? `${item.visit_count}회` : "아직 없음"],
        ];

        for (const [label, value] of details) {
            const row = document.createElement("div");
            appendText(row, "dt", label);
            appendText(row, "dd", value);
            definitionList.appendChild(row);
        }

        detailCard.appendChild(definitionList);
    }

    function renderRecords(items) {
        clearNode(recordList);
        resultCount.textContent = items.length;

        if (!items.length) {
            renderEmptyState();
            renderDetail(null);
            return;
        }

        const hasSelected = items.some((item) => makeRecordKey(item) === state.selectedKey);
        if (!hasSelected) {
            state.selectedKey = makeRecordKey(items[0]);
        }

        for (const item of items) {
            const key = makeRecordKey(item);
            const row = document.createElement("button");
            row.type = "button";
            row.className = `record-row${key === state.selectedKey ? " selected" : ""}`;
            row.setAttribute("role", "listitem");

            appendText(row, "span", item.kind === "country" ? "◎" : "⌖", "flag");

            const name = document.createElement("span");
            name.className = "record-name";
            appendText(name, "strong", valueOrDash(item.name));
            appendText(name, "small", `${valueOrDash(item.country_name)} · ${kindLabel[item.kind] || valueOrDash(item.kind)}`);
            row.appendChild(name);

            appendText(row, "span", valueOrDash(item.region_name), "record-region");
            appendText(row, "span", statusLabel[item.visit_status] || valueOrDash(item.visit_status), `status ${statusClass(item.visit_status)}`);
            appendText(row, "span", "↗", "arrow");

            row.addEventListener("click", () => {
                state.selectedKey = key;
                renderRecords(state.items);
            });

            recordList.appendChild(row);
        }

        renderDetail(items.find((item) => makeRecordKey(item) === state.selectedKey));
    }

    function setKind(kind) {
        state.kind = kind;
        for (const button of kindButtons) {
            button.classList.toggle("active", button.dataset.kind === kind);
        }
        loadResults();
    }

    function resetFilters() {
        searchInput.value = "";
        clearSearch.hidden = true;
        regionFilter.value = "";
        statusFilter.value = "";
        sortFilter.value = "name";
        state.kind = "all";
        state.selectedKey = null;

        for (const button of kindButtons) {
            button.classList.toggle("active", button.dataset.kind === "all");
        }

        loadResults();
    }

    async function loadResults() {
        errorBox.hidden = true;
        recordList.setAttribute("aria-busy", "true");

        try {
            const data = await fetchTravelRecords(true);
            state.items = data.items || [];
            renderRecords(state.items);
        } catch (error) {
            clearNode(recordList);
            resultCount.textContent = "0";
            appendText(recordList, "div", "결과를 표시할 수 없습니다.", "empty-state");
            renderDetail(null);
            errorBox.textContent = error.message;
            errorBox.hidden = false;
        } finally {
            recordList.removeAttribute("aria-busy");
        }
    }

    async function initialize() {
        try {
            const data = await fetchTravelRecords(false);
            state.allItems = data.items || [];
            updateHeroStats(state.allItems);
            populateRegionFilter(state.allItems);
            populateQuickTags(state.allItems);
        } catch (error) {
            countryCount.textContent = "-";
            locationCount.textContent = "-";
            regionCount.textContent = "-";
        }

        loadResults();
    }

    kindButtons.forEach((button) => {
        button.addEventListener("click", () => setKind(button.dataset.kind));
    });

    filterForm.addEventListener("change", loadResults);

    searchInput.addEventListener("input", () => {
        clearSearch.hidden = !searchInput.value;
        window.clearTimeout(state.debounceId);
        state.debounceId = window.setTimeout(loadResults, 250);
    });

    clearSearch.addEventListener("click", () => {
        searchInput.value = "";
        clearSearch.hidden = true;
        loadResults();
    });

    resetButton.addEventListener("click", resetFilters);

    initialize();
})();
