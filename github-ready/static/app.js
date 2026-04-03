document.addEventListener("DOMContentLoaded", () => {
    const text = {
        switchDay: "\u5207\u6362\u65e5\u95f4\u6a21\u5f0f",
        switchNight: "\u5207\u6362\u591c\u95f4\u6a21\u5f0f",
        noRecord: "\u65e0\u8bb0\u5f55",
        incomplete: "\u5f85\u8865\u5168",
        chooseDay: "\u8bf7\u9009\u62e9\u4e00\u5929",
        noNote: "\u6682\u65e0\u5907\u6ce8",
        noBreakdown: "\u6682\u65e0\u660e\u7ec6",
        wear: "\u78e8\u635f",
        income: "\u6536\u5165",
    };

    const themeToggle = document.querySelector("[data-theme-toggle]");
    const savedTheme = window.localStorage.getItem("bm2-theme") || "light";
    document.body.dataset.theme = savedTheme;
    if (themeToggle) {
        const syncThemeLabel = () => {
            themeToggle.textContent = document.body.dataset.theme === "dark" ? text.switchDay : text.switchNight;
        };
        syncThemeLabel();
        themeToggle.addEventListener("click", () => {
            document.body.dataset.theme = document.body.dataset.theme === "dark" ? "light" : "dark";
            window.localStorage.setItem("bm2-theme", document.body.dataset.theme);
            syncThemeLabel();
        });
    }

    document.querySelectorAll("[data-score]").forEach((button) => {
        button.addEventListener("click", () => {
            const targetName = button.dataset.target;
            const score = button.dataset.score;
            const input = document.querySelector(`[name="${targetName}"]`);
            if (input) {
                input.value = score;
            }
        });
    });

    const fillAllButton = document.querySelector("[data-fill-all]");
    if (fillAllButton) {
        fillAllButton.addEventListener("click", () => {
            const score = fillAllButton.dataset.fillAll;
            document.querySelectorAll(".score-input").forEach((input) => {
                input.value = score;
            });
        });
    }

    const clearAllButton = document.querySelector("[data-clear-all]");
    if (clearAllButton) {
        clearAllButton.addEventListener("click", () => {
            document.querySelectorAll(".score-input, .balance-input, .manual-wear-input, .income-input").forEach((input) => {
                input.value = "";
            });
            document.querySelectorAll("[data-wear-result]").forEach((node) => {
                node.textContent = text.noRecord;
                node.classList.remove("negative");
            });
        });
    }

    const updateWear = (groupName) => {
        const beforeInput = document.querySelector(`[data-balance-group="${groupName}"][data-balance-role="before"]`);
        const afterInput = document.querySelector(`[data-balance-group="${groupName}"][data-balance-role="after"]`);
        const manualInput = document.querySelector(`[data-manual-wear="${groupName}"]`);
        const resultNode = document.querySelector(`[data-wear-result="${groupName}"]`);
        if (!beforeInput || !afterInput || !manualInput || !resultNode) {
            return;
        }

        const manualValue = manualInput.value.trim();
        if (manualValue !== "") {
            const manualNumber = Number(manualValue);
            if (Number.isNaN(manualNumber)) {
                resultNode.textContent = text.incomplete;
                resultNode.classList.remove("negative");
                return;
            }
            resultNode.textContent = manualNumber.toFixed(1);
            resultNode.classList.toggle("negative", manualNumber < 0);
            return;
        }

        const beforeValue = beforeInput.value.trim();
        const afterValue = afterInput.value.trim();
        if (!beforeValue && !afterValue) {
            resultNode.textContent = text.noRecord;
            resultNode.classList.remove("negative");
            return;
        }
        const beforeNumber = Number(beforeValue);
        const afterNumber = Number(afterValue);
        if (Number.isNaN(beforeNumber) || Number.isNaN(afterNumber) || beforeValue === "" || afterValue === "") {
            resultNode.textContent = text.incomplete;
            resultNode.classList.remove("negative");
            return;
        }
        const wear = beforeNumber - afterNumber;
        resultNode.textContent = wear.toFixed(1);
        resultNode.classList.toggle("negative", wear < 0);
    };

    document.querySelectorAll(".balance-input, .manual-wear-input").forEach((input) => {
        const groupName = input.dataset.balanceGroup || input.dataset.manualWear;
        input.addEventListener("input", () => updateWear(groupName));
        updateWear(groupName);
    });

    const detailDate = document.querySelector("[data-detail-date]");
    const detailWear = document.querySelector("[data-detail-wear]");
    const detailIncome = document.querySelector("[data-detail-income]");
    const setDetail = (date, wear, income) => {
        if (!detailDate || !detailWear || !detailIncome) {
            return;
        }
        detailDate.textContent = date || text.chooseDay;
        detailWear.textContent = wear === "" || wear == null ? text.noRecord : wear;
        detailIncome.textContent = income === "" || income == null ? "0" : income;
        detailWear.classList.toggle("negative", Number(wear) < 0);
    };

    document.querySelectorAll(".calendar-cell, .record-item").forEach((button) => {
        button.addEventListener("click", () => {
            setDetail(button.dataset.date, button.dataset.wear, button.dataset.income);
            document.querySelectorAll(".calendar-cell.active, .record-item.active").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
        });
    });

    const firstRecord = document.querySelector(".record-item") || document.querySelector(".calendar-cell.has-record");
    if (firstRecord) {
        firstRecord.click();
    }

    const modal = document.querySelector("[data-calendar-modal]");
    const modalDate = document.querySelector("[data-calendar-detail-date]");
    const modalWear = document.querySelector("[data-calendar-detail-wear]");
    const modalIncome = document.querySelector("[data-calendar-detail-income]");
    const modalNote = document.querySelector("[data-calendar-detail-note]");
    const modalWearCount = document.querySelector("[data-calendar-detail-wear-count]");
    const modalIncomeCount = document.querySelector("[data-calendar-detail-income-count]");
    const modalAvgWear = document.querySelector("[data-calendar-detail-avg-wear]");
    const modalAvgIncome = document.querySelector("[data-calendar-detail-avg-income]");
    const modalBreakdown = document.querySelector("[data-calendar-breakdown]");
    const modalBreakdownList = document.querySelector("[data-calendar-breakdown-list]");
    let calendarClickTimer = null;

    const renderBreakdown = (button, expanded) => {
        if (!modalBreakdown || !modalBreakdownList) {
            return;
        }
        if (!expanded) {
            modalBreakdown.hidden = true;
            modalBreakdownList.innerHTML = "";
            return;
        }
        let rows = [];
        try {
            rows = JSON.parse(button.dataset.breakdown || "[]");
        } catch {
            rows = [];
        }
        if (!rows.length) {
            modalBreakdown.hidden = false;
            modalBreakdownList.innerHTML = `<div class="calendar-breakdown-row"><strong>${text.noBreakdown}</strong><span>-</span><span>-</span></div>`;
            return;
        }
        modalBreakdown.hidden = false;
        modalBreakdownList.innerHTML = rows.map((row) => `
            <div class="calendar-breakdown-row">
                <strong>${row.name}</strong>
                <span>${text.wear} ${row.wear}</span>
                <span>${text.income} ${row.income}</span>
            </div>
        `).join("");
    };

    const openCalendarModal = (button, expanded = false) => {
        if (!modal || !modalDate || !modalWear || !modalIncome || !modalNote || !modalWearCount || !modalIncomeCount || !modalAvgWear || !modalAvgIncome) {
            return;
        }
        modalDate.textContent = button.dataset.date || text.chooseDay;
        modalWear.textContent = button.dataset.wear || text.noRecord;
        modalIncome.textContent = button.dataset.income || "0";
        modalNote.textContent = button.dataset.note || text.noNote;
        modalWearCount.textContent = button.dataset.wearCount || "0";
        modalIncomeCount.textContent = button.dataset.incomeCount || "0";
        modalAvgWear.textContent = button.dataset.avgWear || "-";
        modalAvgIncome.textContent = button.dataset.avgIncome || "-";
        renderBreakdown(button, expanded);
        modal.hidden = false;
    };

    document.querySelectorAll("[data-calendar-open]").forEach((button) => {
        button.addEventListener("click", () => {
            if (calendarClickTimer) {
                window.clearTimeout(calendarClickTimer);
            }
            calendarClickTimer = window.setTimeout(() => {
                openCalendarModal(button, false);
                calendarClickTimer = null;
            }, 220);
        });
        button.addEventListener("dblclick", () => {
            if (calendarClickTimer) {
                window.clearTimeout(calendarClickTimer);
                calendarClickTimer = null;
            }
            openCalendarModal(button, true);
        });
    });

    document.querySelectorAll("[data-calendar-close]").forEach((button) => {
        button.addEventListener("click", () => {
            if (modal) {
                modal.hidden = true;
            }
        });
    });
});
