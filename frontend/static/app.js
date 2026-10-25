/**
 * ENDU Runner Scanner & Risultati - Frontend Logic
 * Gestisce:
 *  1. Verifica iscrizioni a gare future (SSE stream)
 *  2. Consultazione dello storico tempi e piazzamenti in gare passate (SSE stream)
 */

document.addEventListener("DOMContentLoaded", () => {
    // Riferimenti elementi Tab e Banner
    const tabFuture = document.getElementById("tabFuture");
    const tabResults = document.getElementById("tabResults");
    const bannerTitle = document.getElementById("bannerTitle");
    const bannerDesc = document.getElementById("bannerDesc");
    const bannerBadgeText = document.getElementById("bannerBadgeText");
    const filterNoticeText = document.getElementById("filterNoticeText");

    // Riferimenti form
    const searchForm = document.getElementById("searchForm");
    const firstNameInput = document.getElementById("firstName");
    const lastNameInput = document.getElementById("lastName");
    const teamCodeInput = document.getElementById("teamCode");
    const timePeriodSelect = document.getElementById("timePeriodSelect");
    const timePeriodLabel = document.getElementById("timePeriodLabel");

    // Pulsanti
    const btnSubmit = document.getElementById("btnSubmit");
    const submitLabel = document.getElementById("submitLabel");
    const submitIcon = document.getElementById("submitIcon");
    const btnClear = document.getElementById("btnClear");
    const btnAbortScan = document.getElementById("btnAbortScan");
    const btnRefreshCalendar = document.getElementById("btnRefreshCalendar");
    const refreshIcon = document.getElementById("refreshIcon");

    // Status pill
    const calendarStatusPill = document.getElementById("calendarStatusPill");
    const cacheIndicator = document.getElementById("cacheIndicator");
    const cacheText = document.getElementById("cacheText");

    // Pannello di progresso
    const progressPanel = document.getElementById("progressPanel");
    const progressTitle = document.getElementById("progressTitle");
    const progressPercentage = document.getElementById("progressPercentage");
    const progressBar = document.getElementById("progressBar");
    const progressCheckedText = document.getElementById("progressCheckedText");
    const progressMatchesText = document.getElementById("progressMatchesText");

    // Box di errore
    const errorPanel = document.getElementById("errorPanel");
    const errorMessageText = document.getElementById("errorMessageText");

    // Risultati
    const resultsHeader = document.getElementById("resultsHeader");
    const resultsCountTitle = document.getElementById("resultsCountTitle");
    const resultsSubTitle = document.getElementById("resultsSubTitle");
    const resultsContainer = document.getElementById("resultsContainer");
    const emptyState = document.getElementById("emptyState");
    const emptyStateTitle = document.getElementById("emptyStateTitle");
    const emptyStateDesc = document.getElementById("emptyStateDesc");
    const btnExport = document.getElementById("btnExport");

    // Stato applicazione
    let currentMode = "future"; // "future" | "results"
    let currentEventSource = null;
    let foundMatches = [];
    let isScanning = false;

    // Configurazione opzioni temporali per ciascuna modalità
    const FUTURE_PERIODS = [
        { label: "Prossimo 1 mese", value: "1" },
        { label: "Prossimi 2 mesi", value: "2" },
        { label: "Prossimi 3 mesi", value: "3" },
        { label: "Prossimi 5 mesi (Predefinito)", value: "5", selected: true },
        { label: "Prossimi 6 mesi", value: "6" },
        { label: "Prossimi 12 mesi (1 anno)", value: "12" }
    ];

    const PAST_PERIODS = [
        { label: "Ultimi 3 mesi", value: "3" },
        { label: "Ultimi 6 mesi", value: "6" },
        { label: "Ultimi 12 mesi (1 anno - Predefinito)", value: "12", selected: true },
        { label: "Ultimi 24 mesi (2 anni)", value: "24" },
        { label: "Anno 2026", value: "year_2026" },
        { label: "Anno 2025", value: "year_2025" },
        { label: "Anno 2024", value: "year_2024" }
    ];

    // Inizializza interfaccia
    setupMode("future");
    checkCalendarStatus();

    // Gestione cambio Tab
    tabFuture.addEventListener("click", () => {
        if (currentMode === "future" || isScanning) return;
        setupMode("future");
    });

    tabResults.addEventListener("click", () => {
        if (currentMode === "results" || isScanning) return;
        setupMode("results");
    });

    function setupMode(mode) {
        currentMode = mode;
        clearResults();
        hideError();

        if (mode === "future") {
            // Stile tab attivo
            tabFuture.className = "px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm bg-white text-emerald-900 flex items-center space-x-2";
            tabResults.className = "px-5 py-2.5 rounded-xl text-xs font-bold transition-all text-slate-600 hover:text-slate-900 flex items-center space-x-2";
            
            // Aggiorna banner
            bannerTitle.textContent = "Verifica Iscrizioni Gare Future";
            bannerDesc.innerHTML = 'Inserisci il Nome e Cognome del podista oppure il Codice Società per scansionare istantaneamente le manifestazioni running dei prossimi mesi su <span class="text-emerald-300 font-medium">endu.net</span>.';
            bannerBadgeText.textContent = "Scansione Diretta API ENDU";
            timePeriodLabel.textContent = "Orizzonte Temporale";
            filterNoticeText.innerHTML = "Filtro automatico: solo gare di <b>Corsa su Strada</b> (esclusi trail e triathlon).";
            
            submitLabel.textContent = "Verifica Iscrizioni";
            submitIcon.setAttribute("data-lucide", "search");

            populateTimePeriods(FUTURE_PERIODS);
        } else {
            // Stile tab risultati attivo
            tabResults.className = "px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm bg-white text-emerald-900 flex items-center space-x-2";
            tabFuture.className = "px-5 py-2.5 rounded-xl text-xs font-bold transition-all text-slate-600 hover:text-slate-900 flex items-center space-x-2";

            // Aggiorna banner
            bannerTitle.textContent = "Storico Risultati & Classifiche";
            bannerDesc.innerHTML = 'Cerca in quali gare passate ha partecipato l\'atleta e visualizza tempi ufficiali, real-time e piazzamenti. <span class="text-emerald-300 font-medium">Nessun login richiesto</span>: accesso pubblico alle classifiche ENDU.';
            bannerBadgeText.textContent = "Classifiche Ufficiali ENDU";
            timePeriodLabel.textContent = "Periodo Gare Passate";
            filterNoticeText.innerHTML = "Accesso pubblico diretto alle <b>classifiche digitali ufficiali</b> (tempi real-time e piazzamenti).";

            submitLabel.textContent = "Cerca Risultati Storici";
            submitIcon.setAttribute("data-lucide", "trophy");

            populateTimePeriods(PAST_PERIODS);
        }
        lucide.createIcons();
    }

    function populateTimePeriods(periods) {
        timePeriodSelect.innerHTML = "";
        periods.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.value;
            opt.textContent = p.label;
            if (p.selected) opt.selected = true;
            timePeriodSelect.appendChild(opt);
        });
    }

    // Stato cache calendario
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
            console.warn("Impossibile verificare stato cache:", err);
        }
    }

    // Refresh forzato calendario gare future
    btnRefreshCalendar.addEventListener("click", async () => {
        if (isScanning) return;
        refreshIcon.classList.add("animate-spin");
        btnRefreshCalendar.disabled = true;
        cacheText.textContent = "Aggiornamento calendario da ENDU...";
        
        try {
            const val = timePeriodSelect.value;
            const months = val.startsWith("year_") ? 12 : (parseInt(val) || 5);
            const res = await fetch(`/api/calendar/refresh?months=${months}`, { method: "POST" });
            const data = await res.json();
            
            if (res.ok) {
                cacheIndicator.className = "w-2 h-2 rounded-full bg-emerald-500";
                cacheText.textContent = `${data.total_events} gare caricate con successo`;
            } else {
                showError(data.detail || "Errore durante l'aggiornamento.");
            }
        } catch (err) {
            showError("Errore di connessione con il backend locale.");
        } finally {
            refreshIcon.classList.remove("animate-spin");
            btnRefreshCalendar.disabled = false;
        }
    });

    // Reset del modulo
    btnClear.addEventListener("click", () => {
        if (isScanning) abortScan();
        firstNameInput.value = "";
        lastNameInput.value = "";
        teamCodeInput.value = "";
        timePeriodSelect.selectedIndex = currentMode === "future" ? 3 : 2;
        clearResults();
        hideError();
    });

    // Annulla scansione attiva
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
        tabFuture.disabled = scanning;
        tabResults.disabled = scanning;

        if (scanning) {
            submitLabel.textContent = "Scansione in corso...";
            submitIcon.setAttribute("data-lucide", "loader-2");
            submitIcon.classList.add("animate-spin");
        } else {
            submitLabel.textContent = currentMode === "future" ? "Verifica Iscrizioni" : "Cerca Risultati Storici";
            submitIcon.setAttribute("data-lucide", currentMode === "future" ? "search" : "trophy");
            submitIcon.classList.remove("animate-spin");
        }
        lucide.createIcons();
    }

    // Submit del form con SSE Stream
    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        hideError();

        const first = firstNameInput.value.trim();
        const last = lastNameInput.value.trim();
        const team = teamCodeInput.value.trim();
        const periodValue = timePeriodSelect.value;

        // Validazione minima: almeno un campo con almeno 2 lettere
        const hasValidFirst = first.length >= 2;
        const hasValidLast = last.length >= 2;
        const hasValidTeam = team.length >= 2;

        if (!hasValidFirst && !hasValidLast && !hasValidTeam) {
            showError("Inserisci almeno il Cognome, il Nome oppure la Società (minimo 2 caratteri) per avviare la ricerca.");
            return;
        }

        clearResults();
        setScanningState(true);

        progressPanel.classList.remove("hidden");
        progressTitle.textContent = currentMode === "future" 
            ? "Connessione al calendario gare future ENDU..."
            : "Connessione all'archivio classifiche ENDU...";
        progressPercentage.textContent = "0%";
        progressBar.style.width = "0%";
        progressCheckedText.textContent = "0 gare verificate";
        progressMatchesText.textContent = "0 corrispondenze trovate";

        const params = new URLSearchParams();
        if (first) params.append("first_name", first);
        if (last) params.append("last_name", last);
        if (team) params.append("team_code", team);

        let streamUrl = "";
        if (currentMode === "future") {
            params.append("months", periodValue || "5");
            streamUrl = `/api/search/stream?${params.toString()}`;
        } else {
            if (periodValue.startsWith("year_")) {
                params.append("year", periodValue.replace("year_", ""));
            } else {
                params.append("months", periodValue || "12");
            }
            streamUrl = `/api/results/search/stream?${params.toString()}`;
        }

        if (currentEventSource) {
            currentEventSource.close();
        }

        currentEventSource = new EventSource(streamUrl);

        currentEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleStreamPacket(data);
            } catch (err) {
                console.error("Errore parsing SSE:", err);
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

    // Gestione pacchetti SSE in arrivo
    function handleStreamPacket(packet) {
        switch (packet.type) {
            case "init":
                const modeLabel = currentMode === "future" ? "gare running future" : "gare con classifiche digitali";
                progressTitle.textContent = `Scansione di ${packet.total} ${modeLabel}...`;
                progressCheckedText.textContent = `0 / ${packet.total} gare verificate`;
                if (currentMode === "future") checkCalendarStatus();
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
                if (currentMode === "future") {
                    renderEventCard(packet.match);
                } else {
                    renderPastResultCard(packet.match);
                }
                resultsHeader.classList.remove("hidden");
                updateResultsCount();
                
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
                    emptyStateTitle.textContent = currentMode === "future" 
                        ? "Nessuna Iscrizione Trovata"
                        : "Nessun Risultato in Classifica Trovato";
                    emptyStateDesc.textContent = currentMode === "future"
                        ? "Nessun atleta corrispondente ai criteri inseriti risulta iscritto a manifestazioni future nell'intervallo selezionato."
                        : "Nessun risultato di gara trovato per l'atleta nelle classifiche ENDU dell'intervallo selezionato.";
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
        const entity = currentMode === "future" ? "Gara Trovata" : "Gara con Risultati";
        const entities = currentMode === "future" ? "Gare Trovate" : "Gare con Risultati";
        resultsCountTitle.textContent = `${count} ${count === 1 ? entity : entities}`;
        
        const periodText = timePeriodSelect.options[timePeriodSelect.selectedIndex]?.text || "";
        if (elapsed) {
            resultsSubTitle.textContent = `Scansione completata in ${elapsed}s su ${periodText}`;
        } else {
            resultsSubTitle.textContent = `Risultati aggiornati in tempo reale per ${periodText}`;
        }
    }

    // Render Card Gara Futura (Iscrizione)
    function renderEventCard(match) {
        const card = document.createElement("div");
        card.className = "event-card bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-6 space-y-4";

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

    // Render Card Gara Passata (Risultati, Tempi & Piazzamenti)
    function renderPastResultCard(match) {
        const card = document.createElement("div");
        card.className = "event-card bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-6 space-y-4";

        const resultsHtml = match.results.map(res => `
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-3">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/60 pb-2.5">
                    <div class="flex items-center space-x-2">
                        <span class="font-extrabold text-slate-900 text-base">${escapeHtml(res.full_name)}</span>
                        ${res.nationality ? `<span class="px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 text-[10px] font-bold uppercase">${escapeHtml(res.nationality)}</span>` : ''}
                        <span class="px-2 py-0.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-bold border border-indigo-100">${escapeHtml(res.race_name)}</span>
                    </div>
                    ${res.bib ? `
                        <div class="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md bg-amber-50 text-amber-900 border border-amber-300 text-xs">
                            <span class="text-[10px] uppercase font-bold text-amber-700">Pettorale</span>
                            <span class="font-mono font-bold">#${escapeHtml(res.bib)}</span>
                        </div>
                    ` : ''}
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    <!-- Tempo Ufficiale -->
                    <div class="p-2.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                        <span class="block text-[10px] font-bold uppercase text-slate-400">Tempo Ufficiale</span>
                        <span class="text-lg font-mono font-black text-emerald-600">${escapeHtml(res.official_time || '-')}</span>
                        ${res.real_time && res.real_time !== res.official_time ? `
                            <span class="block text-[10px] text-slate-400 font-mono">Real: ${escapeHtml(res.real_time)}</span>
                        ` : ''}
                    </div>

                    <!-- Posizione Assoluta -->
                    <div class="p-2.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                        <span class="block text-[10px] font-bold uppercase text-slate-400">Pos. Assoluta</span>
                        <span class="text-lg font-extrabold text-slate-900">${res.absolute_position ? `${escapeHtml(res.absolute_position)}°` : '-'}</span>
                        ${res.gap_time ? `<span class="block text-[10px] text-slate-400 font-mono">Distacco: ${escapeHtml(res.gap_time)}</span>` : ''}
                    </div>

                    <!-- Posizione Categoria -->
                    <div class="p-2.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                        <span class="block text-[10px] font-bold uppercase text-slate-400">Categoria ${res.category ? `(${escapeHtml(res.category)})` : ''}</span>
                        <span class="text-lg font-extrabold text-indigo-700">${res.category_position ? `${escapeHtml(res.category_position)}°` : '-'}</span>
                    </div>

                    <!-- Posizione Sesso -->
                    <div class="p-2.5 rounded-xl bg-white border border-slate-200 shadow-xs">
                        <span class="block text-[10px] font-bold uppercase text-slate-400">Pos. ${res.gender === 'F' ? 'Femminile' : 'Maschile'}</span>
                        <span class="text-lg font-extrabold text-slate-700">${res.gender_position ? `${escapeHtml(res.gender_position)}°` : '-'}</span>
                    </div>
                </div>

                ${res.team_name ? `
                    <div class="text-xs text-slate-500 pt-1">
                        <strong class="font-semibold text-slate-700">Società:</strong> ${escapeHtml(res.team_name)}
                    </div>
                ` : ''}
            </div>
        `).join("");

        card.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div class="space-y-1.5">
                    <div class="flex items-center space-x-2">
                        <span class="px-2.5 py-1 rounded-lg bg-indigo-100 text-indigo-900 text-xs font-bold flex items-center space-x-1.5">
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
                    <a href="${escapeHtml(match.results_url)}" target="_blank" rel="noopener noreferrer"
                        class="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1.5">
                        <i data-lucide="trophy" class="w-3.5 h-3.5"></i>
                        <span>Classifica ENDU</span>
                    </a>
                    <a href="${escapeHtml(match.event_url)}" target="_blank" rel="noopener noreferrer"
                        class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors flex items-center space-x-1">
                        <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        <span>Gara</span>
                    </a>
                </div>
            </div>

            <div class="space-y-2 pt-2 border-t border-slate-100">
                ${resultsHtml}
            </div>
        `;

        resultsContainer.appendChild(card);
        lucide.createIcons();
    }

    // Copia riepilogo testuale
    btnExport.addEventListener("click", () => {
        if (foundMatches.length === 0) return;

        let summary = currentMode === "future" ? `=== ISCRIZIONI FUTURE ENDU ===\n` : `=== RISULTATI STORICI GARE ENDU ===\n`;
        summary += `Criteri: Nome: ${firstNameInput.value || '-'} | Cognome: ${lastNameInput.value || '-'} | Società: ${teamCodeInput.value || '-'}\n`;
        summary += `Totale manifestazioni trovate: ${foundMatches.length}\n\n`;

        foundMatches.forEach((ev, idx) => {
            summary += `${idx + 1}. ${ev.name} (${ev.date_formatted}) - ${ev.location_formatted}\n`;
            if (currentMode === "future") {
                ev.entrants.forEach(ent => {
                    summary += `   • Atleta: ${ent.full_name}`;
                    if (ent.bib) summary += ` | Pettorale: #${ent.bib}`;
                    if (ent.team_name) summary += ` | Società: ${ent.team_name}`;
                    if (ent.course_name) summary += ` | Gara: ${ent.course_name}`;
                    summary += `\n`;
                });
                summary += `   Verifica ENDU: ${ev.verify_url}\n\n`;
            } else {
                ev.results.forEach(res => {
                    summary += `   • Gara: ${res.race_name} | Atleta: ${res.full_name}\n`;
                    summary += `     Tempo Ufficiale: ${res.official_time || '-'} | Posizione Assoluta: ${res.absolute_position ? res.absolute_position + '°' : '-'}\n`;
                    if (res.category_position) summary += `     Pos. Categoria (${res.category || ''}): ${res.category_position}°\n`;
                    if (res.team_name) summary += `     Società: ${res.team_name}\n`;
                });
                summary += `   Classifica ENDU: ${ev.results_url}\n\n`;
            }
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
            alert("Impossibile copiare negli appunti.");
        });
    });

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
