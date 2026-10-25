/**
 * ENDU Runner Scanner - Frontend Logic
 * Gestisce l'interazione utente, la connessione Server-Sent Events (SSE) in tempo reale,
 * l'aggiornamento della progress bar e la renderizzazione delle card dei risultati.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Riferimenti elementi DOM
    const searchForm = document.getElementById("searchForm");
    const firstNameInput = document.getElementById("firstName");
    const lastNameInput = document.getElementById("lastName");
    const teamCodeInput = document.getElementById("teamCode");
    const monthsSelect = document.getElementById("months");
    const btnSubmit = document.getElementById("btnSubmit");
    const submitLabel = document.getElementById("submitLabel");
    const submitIcon = document.getElementById("submitIcon");
    const btnClear = document.getElementById("btnClear");
    const btnAbortScan = document.getElementById("btnAbortScan");
    const btnRefreshCalendar = document.getElementById("btnRefreshCalendar");
    const refreshIcon = document.getElementById("refreshIcon");

    const calendarStatusPill = document.getElementById("calendarStatusPill");
    const cacheIndicator = document.getElementById("cacheIndicator");
    const cacheText = document.getElementById("cacheText");

    const progressPanel = document.getElementById("progressPanel");
    const progressTitle = document.getElementById("progressTitle");
    const progressPercentage = document.getElementById("progressPercentage");
    const progressBar = document.getElementById("progressBar");
    const progressCheckedText = document.getElementById("progressCheckedText");
    const progressMatchesText = document.getElementById("progressMatchesText");

    const errorPanel = document.getElementById("errorPanel");
    const errorMessageText = document.getElementById("errorMessageText");

    const resultsHeader = document.getElementById("resultsHeader");
    const resultsCountTitle = document.getElementById("resultsCountTitle");
    const resultsSubTitle = document.getElementById("resultsSubTitle");
    const resultsContainer = document.getElementById("resultsContainer");
    const emptyState = document.getElementById("emptyState");
    const btnExport = document.getElementById("btnExport");

    let currentEventSource = null;
    let foundMatches = [];
    let isScanning = false;

    // Carica lo stato della cache all'avvio
    checkCalendarStatus();

    // Gestione stato cache calendario
    async function checkCalendarStatus() {
        try {
            const res = await fetch("/api/calendar/status");
            if (!res.ok) return;
            const data = await res.json();
            
            calendarStatusPill.classList.remove("hidden");
            if (data.is_cached && data.total_events > 0) {
                const minutesLeft = Math.round(data.ttl_seconds_remaining / 60);
                cacheIndicator.className = "w-2 h-2 rounded-full bg-emerald-500";
                cacheText.textContent = `${data.total_events} gare running in cache (${minutesLeft}m)`;
            } else {
                cacheIndicator.className = "w-2 h-2 rounded-full bg-slate-400";
                cacheText.textContent = "Calendario pronto al caricamento";
            }
        } catch (err) {
            console.warn("Impossibile verificare lo stato della cache:", err);
        }
    }

    // Refresh forzato del calendario
    btnRefreshCalendar.addEventListener("click", async () => {
        if (isScanning) return;
        
        refreshIcon.classList.add("animate-spin");
        btnRefreshCalendar.disabled = true;
        cacheText.textContent = "Aggiornamento da ENDU in corso...";
        
        try {
            const months = monthsSelect.value || 5;
            const res = await fetch(`/api/calendar/refresh?months=${months}`, { method: "POST" });
            const data = await res.json();
            
            if (res.ok) {
                cacheIndicator.className = "w-2 h-2 rounded-full bg-emerald-500";
                cacheText.textContent = `${data.total_events} gare caricate per i prossimi ${months} mesi`;
            } else {
                showError(data.detail || "Errore durante l'aggiornamento del calendario.");
            }
        } catch (err) {
            showError("Errore di connessione con il backend locale.");
        } finally {
            refreshIcon.classList.remove("animate-spin");
            btnRefreshCalendar.disabled = false;
        }
    });

    // Reset del form
    btnClear.addEventListener("click", () => {
        if (isScanning) abortScan();
        firstNameInput.value = "";
        lastNameInput.value = "";
        teamCodeInput.value = "";
        monthsSelect.value = "5";
        clearResults();
        hideError();
    });

    // Interrompi scansione in corso
    btnAbortScan.addEventListener("click", () => {
        abortScan();
    });

    function abortScan() {
        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
        setScanningState(false);
        progressTitle.textContent = "Scansione interrotta dall'utente.";
        setTimeout(() => {
            progressPanel.classList.add("hidden");
        }, 1500);
    }

    function clearResults() {
        foundMatches = [];
        resultsContainer.innerHTML = "";
        resultsHeader.classList.add("hidden");
        emptyState.classList.add("hidden");
        progressPanel.classList.add("hidden");
    }

    function showError(msg) {
        errorMessageText.textContent = msg;
        errorPanel.classList.remove("hidden");
    }

    function hideError() {
        errorPanel.classList.add("hidden");
    }

    function setScanningState(scanning) {
        isScanning = scanning;
        btnSubmit.disabled = scanning;
        btnClear.disabled = scanning;
        btnRefreshCalendar.disabled = scanning;

        if (scanning) {
            submitLabel.textContent = "Scansione in corso...";
            submitIcon.setAttribute("data-lucide", "loader-2");
            submitIcon.classList.add("animate-spin");
        } else {
            submitLabel.textContent = "Verifica Iscrizioni";
            submitIcon.setAttribute("data-lucide", "search");
            submitIcon.classList.remove("animate-spin");
        }
        lucide.createIcons();
    }

    // Submit del form con Server-Sent Events (SSE)
    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        hideError();

        const first = firstNameInput.value.trim();
        const last = lastNameInput.value.trim();
        const team = teamCodeInput.value.trim();
        const months = monthsSelect.value || 5;

        // Validazione minima: almeno un criterio con 2 caratteri
        const hasValidFirst = first.length >= 2;
        const hasValidLast = last.length >= 2;
        const hasValidTeam = team.length >= 2;

        if (!hasValidFirst && !hasValidLast && !hasValidTeam) {
            showError("Inserisci almeno il Cognome, il Nome oppure il Codice Società (minimo 2 caratteri) per avviare la ricerca.");
            return;
        }

        clearResults();
        setScanningState(true);

        // Prepara il pannello di avanzamento
        progressPanel.classList.remove("hidden");
        progressTitle.textContent = "Connessione al calendario gare ENDU...";
        progressPercentage.textContent = "0%";
        progressBar.style.width = "0%";
        progressCheckedText.textContent = "0 gare verificate";
        progressMatchesText.textContent = "0 iscrizioni trovate";

        // Costruisci i parametri query SSE
        const params = new URLSearchParams();
        if (first) params.append("first_name", first);
        if (last) params.append("last_name", last);
        if (team) params.append("team_code", team);
        params.append("months", months);

        const streamUrl = `/api/search/stream?${params.toString()}`;
        
        if (currentEventSource) {
            currentEventSource.close();
        }

        currentEventSource = new EventSource(streamUrl);

        currentEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleStreamPacket(data);
            } catch (err) {
                console.error("Errore nel parsing del pacchetto SSE:", err);
            }
        };

        currentEventSource.onerror = (err) => {
            console.error("Errore EventSource:", err);
            if (currentEventSource) {
                currentEventSource.close();
                currentEventSource = null;
            }
            setScanningState(false);
            if (foundMatches.length === 0) {
                showError("Connessione interrotta o errore di rete durante la scansione.");
            }
        };
    });

    // Gestore pacchetti stream SSE
    function handleStreamPacket(packet) {
        switch (packet.type) {
            case "init":
                progressTitle.textContent = `Scansione di ${packet.total} gare running nei prossimi ${packet.months} mesi...`;
                progressCheckedText.textContent = `0 / ${packet.total} gare verificate`;
                checkCalendarStatus();
                break;

            case "progress":
                const percent = packet.total > 0 ? Math.round((packet.checked / packet.total) * 100) : 0;
                progressBar.style.width = `${percent}%`;
                progressPercentage.textContent = `${percent}%`;
                progressCheckedText.textContent = `${packet.checked} / ${packet.total} gare verificate`;
                progressMatchesText.textContent = `${packet.matches_count} ${packet.matches_count === 1 ? 'gara trovata' : 'gare trovate'}`;
                break;

            case "match":
                foundMatches.push(packet.match);
                renderEventCard(packet.match);
                resultsHeader.classList.remove("hidden");
                updateResultsCount();
                
                // Aggiorna anche contatore barra
                const curPercent = packet.total > 0 ? Math.round((packet.checked / packet.total) * 100) : 0;
                progressBar.style.width = `${curPercent}%`;
                progressPercentage.textContent = `${curPercent}%`;
                progressCheckedText.textContent = `${packet.checked} / ${packet.total} gare verificate`;
                progressMatchesText.textContent = `${foundMatches.length} ${foundMatches.length === 1 ? 'gara trovata' : 'gare trovate'}`;
                break;

            case "complete":
                if (currentEventSource) {
                    currentEventSource.close();
                    currentEventSource = null;
                }
                setScanningState(false);
                progressBar.style.width = "100%";
                progressPercentage.textContent = "100%";
                progressCheckedText.textContent = `${packet.total_scanned} / ${packet.total_scanned} gare verificate`;
                progressTitle.textContent = `Scansione completata in ${packet.elapsed_seconds} secondi!`;

                setTimeout(() => {
                    progressPanel.classList.add("hidden");
                }, 1200);

                if (foundMatches.length === 0) {
                    emptyState.classList.remove("hidden");
                    resultsHeader.classList.add("hidden");
                } else {
                    resultsHeader.classList.remove("hidden");
                    updateResultsCount(packet.elapsed_seconds);
                }
                break;

            case "error":
                if (currentEventSource) {
                    currentEventSource.close();
                    currentEventSource = null;
                }
                setScanningState(false);
                progressPanel.classList.add("hidden");
                showError(packet.message || "Errore sconosciuto durante la scansione.");
                break;
        }
    }

    function updateResultsCount(elapsed) {
        const count = foundMatches.length;
        resultsCountTitle.textContent = `${count} ${count === 1 ? 'Gara Trovata' : 'Gare Trovate'}`;
        if (elapsed) {
            resultsSubTitle.textContent = `Verifica completata in ${elapsed}s su ${monthsSelect.value} mesi di calendario ENDU`;
        } else {
            resultsSubTitle.textContent = `Risultati aggiornati in tempo reale`;
        }
    }

    // Renderizza una card per l'evento trovato
    function renderEventCard(match) {
        const card = document.createElement("div");
        card.className = "event-card bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-6 space-y-4";

        // Sezione atleti trovati
        const entrantsHtml = match.entrants.map(ent => `
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <div class="space-y-1">
                    <div class="flex items-center space-x-2">
                        <span class="font-bold text-slate-900 text-sm">${escapeHtml(ent.full_name)}</span>
                        ${ent.nationality ? `<span class="px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 text-[10px] font-bold uppercase">${escapeHtml(ent.nationality)}</span>` : ''}
                        ${ent.category ? `<span class="text-slate-500 font-medium">(${escapeHtml(ent.category)})</span>` : ''}
                        ${ent.year_of_birth ? `<span class="text-slate-400 font-normal">&bull; Anno ${escapeHtml(String(ent.year_of_birth))}</span>` : ''}
                    </div>
                    <div class="text-slate-600 flex flex-wrap items-center gap-x-3 gap-y-1">
                        ${ent.team_name ? `<span><strong class="font-semibold text-slate-700">Società:</strong> ${escapeHtml(ent.team_name)}</span>` : ''}
                        ${ent.team_code ? `<span class="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 font-mono font-medium text-[11px] border border-emerald-200">Cod. ${escapeHtml(ent.team_code)}</span>` : ''}
                        ${ent.course_name ? `<span><strong class="font-semibold text-slate-700">Gara:</strong> ${escapeHtml(ent.course_name)}</span>` : ''}
                    </div>
                </div>
                <div>
                    ${ent.bib ? `
                        <div class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-amber-50 text-amber-900 border border-amber-300 shadow-sm">
                            <span class="text-[10px] uppercase font-bold text-amber-700">Pettorale</span>
                            <span class="font-mono font-extrabold text-sm bib-badge">#${escapeHtml(ent.bib)}</span>
                        </div>
                    ` : `
                        <span class="text-[11px] text-slate-400 italic">Pettorale non assegnato</span>
                    `}
                </div>
            </div>
        `).join("");

        card.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div class="space-y-1.5">
                    <div class="flex items-center space-x-2">
                        <span class="px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-900 text-xs font-bold flex items-center space-x-1.5">
                            <i data-lucide="calendar" class="w-3.5 h-3.5"></i>
                            <span>${escapeHtml(match.date_formatted)}</span>
                        </span>
                        <span class="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium flex items-center space-x-1">
                            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500"></i>
                            <span>${escapeHtml(match.location_formatted)}</span>
                        </span>
                    </div>
                    <h4 class="text-lg font-bold text-slate-900">${escapeHtml(match.name)}</h4>
                </div>
                
                <div class="flex items-center space-x-2 shrink-0">
                    <a href="${escapeHtml(match.verify_url)}" target="_blank" rel="noopener noreferrer"
                        class="px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold border border-emerald-200 transition-colors flex items-center space-x-1">
                        <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
                        <span>Verifica ENDU</span>
                    </a>
                    <a href="${escapeHtml(match.event_url)}" target="_blank" rel="noopener noreferrer"
                        class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors flex items-center space-x-1">
                        <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        <span>Pagina Gara</span>
                    </a>
                </div>
            </div>

            <div class="space-y-2 pt-2 border-t border-slate-100">
                <h5 class="text-xs font-bold uppercase tracking-wider text-slate-500">Iscritti Trovati (${match.entrants.length})</h5>
                <div class="space-y-1.5">
                    ${entrantsHtml}
                </div>
            </div>
        `;

        resultsContainer.appendChild(card);
        lucide.createIcons();
    }

    // Copia riepilogo testuale negli appunti
    btnExport.addEventListener("click", () => {
        if (foundMatches.length === 0) return;

        let summary = `=== RISULTATI ISCRIZIONI ENDU ===\n`;
        summary += `Criteri: Nome: ${firstNameInput.value || '-'} | Cognome: ${lastNameInput.value || '-'} | Società: ${teamCodeInput.value || '-'}\n`;
        summary += `Totale gare trovate: ${foundMatches.length}\n\n`;

        foundMatches.forEach((ev, idx) => {
            summary += `${idx + 1}. ${ev.name} (${ev.date_formatted}) - ${ev.location_formatted}\n`;
            ev.entrants.forEach(ent => {
                summary += `   • Atleta: ${ent.full_name}`;
                if (ent.bib) summary += ` | Pettorale: #${ent.bib}`;
                if (ent.team_name) summary += ` | Società: ${ent.team_name} (${ent.team_code || ''})`;
                if (ent.course_name) summary += ` | Gara: ${ent.course_name}`;
                summary += `\n`;
            });
            summary += `   Link gara: ${ev.event_url}\n`;
            summary += `   Verifica: ${ev.verify_url}\n\n`;
        });

        navigator.clipboard.writeText(summary).then(() => {
            const originalText = btnExport.innerHTML;
            btnExport.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-600"></i><span class="text-emerald-700 font-bold">Copiato!</span>`;
            lucide.createIcons();
            setTimeout(() => {
                btnExport.innerHTML = originalText;
                lucide.createIcons();
            }, 2000);
        }).catch(() => {
            alert("Impossibile copiare negli appunti automaticamente.");
        });
    });

    // Helper per escape HTML contro XSS
    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
