/**
 * Runner Scanner - Frontend Logic
 * Gestisce:
 *  1. Verifica iscrizioni a gare future (SSE stream)
 *  2. Consultazione dello storico tempi e piazzamenti in gare passate (SSE stream)
 */

document.addEventListener("DOMContentLoaded", () => {
    // Riferimenti elementi Tab e Banner
    const tabFuture = document.getElementById("tabFuture");
    const tabResults = document.getElementById("tabResults");
    const tabFidal = document.getElementById("tabFidal");
    const tabTrail = document.getElementById("tabTrail");
    const modeSubText = document.getElementById("modeSubText");
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
    const exactDateInput = document.getElementById("exactDate");
    const eventNameInput = document.getElementById("eventName");
    const platformSelect = document.getElementById("platformSelect");
    const platformFilterContainer = document.getElementById("platformFilterContainer");

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

    function getStravaSearchUrl(fullName) {
        if (!fullName) return "#";
        return `https://www.strava.com/athletes/search?text=${encodeURIComponent(fullName.trim())}`;
    }

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
        { label: "Ultimi 12 mesi (Predefinito)", value: "12", selected: true },
        { label: "Ultimi 24 mesi (2 anni)", value: "24" }
    ];
    // Aggiunge tutti gli anni dal corrente a ritroso fino al 2014 (12+ anni di storico)
    for (let yr = 2026; yr >= 2014; yr--) {
        PAST_PERIODS.push({ label: `Anno ${yr}`, value: `year_${yr}` });
    }
    PAST_PERIODS.push({ label: "Ultimi 6 mesi", value: "6" });
    PAST_PERIODS.push({ label: "Ultimi 3 mesi", value: "3" });

    const FIDAL_PERIODS = [
        { label: "Tutta la carriera (Tutti gli anni)", value: "all", selected: true }
    ];
    for (let yr = 2026; yr >= 2014; yr--) {
        FIDAL_PERIODS.push({ label: `Solo Anno ${yr}`, value: `year_${yr}` });
    }

    const WEDOSPORT_PERIODS = [
        { label: "Tutta la carriera Trail (2004 - Oggi)", value: "all", selected: true }
    ];
    for (let yr = 2026; yr >= 2004; yr--) {
        WEDOSPORT_PERIODS.push({ label: `Solo Anno ${yr}`, value: `year_${yr}` });
    }

    // Inizializza interfaccia
    setupMode("future");
    checkCalendarStatus();

    // Se l'utente imposta una data nel passato mentre è su 'future', passa automaticamente a 'results'
    if (exactDateInput) {
        exactDateInput.addEventListener("change", () => {
            if (exactDateInput.value) {
                const parts = exactDateInput.value.split("-");
                if (parts.length === 3) {
                    const selYear = parseInt(parts[0], 10);
                    const currentYear = new Date().getFullYear();
                    if (selYear < currentYear && currentMode === "future") {
                        setupMode("results");
                    }
                }
            }
        });
    }

    // Gestione cambio Tab
    tabFuture.addEventListener("click", () => {
        if (currentMode === "future" || isScanning) return;
        setupMode("future");
    });

    tabResults.addEventListener("click", () => {
        if (currentMode === "results" || isScanning) return;
        setupMode("results");
    });

    if (tabFidal) {
        tabFidal.addEventListener("click", () => {
            if (currentMode === "fidal" || isScanning) return;
            setupMode("fidal");
        });
    }

    if (tabTrail) {
        tabTrail.addEventListener("click", () => {
            if (currentMode === "trail" || isScanning) return;
            setupMode("trail");
        });
    }

    function setupMode(mode) {
        currentMode = mode;
        clearResults();
        hideError();

        // Reset classi tab
        const inactiveTabClass = "px-4 py-2.5 rounded-xl text-xs font-bold transition-all text-slate-600 hover:text-slate-900 flex items-center justify-center space-x-2";
        const activeTabClass = "px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm bg-white text-emerald-900 flex items-center justify-center space-x-2";

        tabFuture.className = mode === "future" ? activeTabClass : inactiveTabClass;
        tabResults.className = mode === "results" ? activeTabClass : inactiveTabClass;
        if (tabFidal) tabFidal.className = mode === "fidal" ? activeTabClass : inactiveTabClass;
        if (tabTrail) tabTrail.className = mode === "trail" ? activeTabClass : inactiveTabClass;

        if (platformFilterContainer) {
            platformFilterContainer.style.display = mode === "future" ? "block" : "none";
        }

        if (mode === "future") {
            if (modeSubText) modeSubText.textContent = "Modalità attiva: verifica se l'atleta o la società è iscritta alle prossime gare su ENDU, ICRON e Wedosport";
            
            // Aggiorna banner
            bannerTitle.textContent = "Verifica Iscrizioni Gare Future";
            bannerDesc.innerHTML = 'Inserisci il Nome e Cognome del podista oppure il Codice Società per scansionare le manifestazioni dei prossimi mesi su <span class="text-emerald-300 font-medium">ENDU, ICRON e Wedosport</span>.';
            bannerBadgeText.textContent = "Scansione Diretta ENDU + ICRON + Wedosport";
            timePeriodLabel.textContent = "Orizzonte Temporale";
            filterNoticeText.innerHTML = "Filtro circuito: Corsa su Strada (ENDU/ICRON) e Trail Running (Wedosport).";
            
            submitLabel.textContent = "Verifica Iscrizioni";
            submitIcon.setAttribute("data-lucide", "search");

            populateTimePeriods(FUTURE_PERIODS);
        } else if (mode === "results") {
            if (modeSubText) modeSubText.textContent = "Modalità attiva: consulta i risultati e tempi cronometrici nelle gare passate su ENDU";

            // Aggiorna banner
            bannerTitle.textContent = "Storico Risultati & Classifiche ENDU";
            bannerDesc.innerHTML = 'Cerca in quali gare passate ha partecipato l\'atleta e visualizza tempi ufficiali, real-time e piazzamenti. <span class="text-emerald-300 font-medium">Nessun login richiesto</span>: accesso pubblico alle classifiche ENDU.';
            bannerBadgeText.textContent = "Classifiche Ufficiali ENDU";
            timePeriodLabel.textContent = "Anno o Periodo Gara";
            filterNoticeText.innerHTML = "Accesso pubblico diretto alle <b>classifiche digitali ufficiali</b> (tempi real-time e piazzamenti).";

            submitLabel.textContent = "Cerca Risultati ENDU";
            submitIcon.setAttribute("data-lucide", "trophy");

            populateTimePeriods(PAST_PERIODS);
        } else if (mode === "fidal") {
            if (modeSubText) modeSubText.textContent = "Modalità attiva: carriera ufficiale FIDAL (copre tutte le gare storiche TDS, ENDU, SDAM, ecc.)";

            // Aggiorna banner
            bannerTitle.textContent = "Carriera & Risultati Ufficiali FIDAL (TDS & Altre)";
            bannerDesc.innerHTML = 'Recupera l\'albo d\'oro ufficiale di tutte le mezze maratone, maratone e 10km FIDAL dell\'atleta (comprese gare storiche cronometrate da <b>TDS</b> come Vicenza e Cittadella negli ultimi 15 anni).';
            bannerBadgeText.textContent = "Albo d'Oro Federale FIDAL";
            timePeriodLabel.textContent = "Filtro Anno Carriera";
            filterNoticeText.innerHTML = "Accesso all'<b>archivio storico ufficiale FIDAL.it</b>: tutte le gare competitive certificate.";

            submitLabel.textContent = "Cerca Carriera FIDAL";
            submitIcon.setAttribute("data-lucide", "award");

            populateTimePeriods(FIDAL_PERIODS);
        } else if (mode === "trail") {
            if (modeSubText) modeSubText.textContent = "Modalità attiva: carriera e palmarès Trail Running, Skyrunning e Ultra su Wedosport (dal 2004 ad oggi)";

            // Aggiorna banner
            bannerTitle.textContent = "Carriera & Risultati Trail Running (Wedosport)";
            bannerDesc.innerHTML = 'Consulta tutte le gare Trail, Skyrunning, Vertical e Ultra disputate dall\'atleta su <span class="text-amber-300 font-medium">Wedosport.net</span>: distanze, chilometri, tempi, piazzamenti e link alle classifiche ufficiali dal 2004.';
            bannerBadgeText.textContent = "Archivio Trail Wedosport (2004-Oggi)";
            timePeriodLabel.textContent = "Filtro Anno Trail";
            filterNoticeText.innerHTML = "Specialità <b>Trail Running, Ultra Trail, SkyRunning e Vertical</b> (piattaforma Wedosport.net).";

            submitLabel.textContent = "Cerca Trail Wedosport";
            submitIcon.setAttribute("data-lucide", "mountain");

            populateTimePeriods(WEDOSPORT_PERIODS);
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
                if (data.total_endu_events !== undefined && data.total_icron_events !== undefined) {
                    const wedoCount = data.total_wedosport_events !== undefined ? ` + ${data.total_wedosport_events} Wedosport` : "";
                    cacheText.textContent = `${data.total_events} gare in cache (${data.total_endu_events} ENDU + ${data.total_icron_events} ICRON${wedoCount})`;
                } else {
                    cacheText.textContent = `${data.total_events} gare running in cache (${minutesLeft}m)`;
                }
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
        cacheText.textContent = "Aggiornamento calendario da ENDU, ICRON e Wedosport...";
        
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
        if (exactDateInput) exactDateInput.value = "";
        if (eventNameInput) eventNameInput.value = "";
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
        if (tabFidal) tabFidal.disabled = scanning;
        if (tabTrail) tabTrail.disabled = scanning;

        if (scanning) {
            submitLabel.textContent = "Scansione in corso...";
            submitIcon.setAttribute("data-lucide", "loader-2");
            submitIcon.classList.add("animate-spin");
        } else {
            if (currentMode === "future") {
                submitLabel.textContent = "Verifica Iscrizioni";
                submitIcon.setAttribute("data-lucide", "search");
            } else if (currentMode === "trail") {
                submitLabel.textContent = "Cerca Trail Wedosport";
                submitIcon.setAttribute("data-lucide", "mountain");
            } else if (currentMode === "fidal") {
                submitLabel.textContent = "Cerca Carriera FIDAL";
                submitIcon.setAttribute("data-lucide", "award");
            } else {
                submitLabel.textContent = "Cerca Risultati ENDU";
                submitIcon.setAttribute("data-lucide", "trophy");
            }
            submitIcon.classList.remove("animate-spin");
        }
        lucide.createIcons();
    }

    // Submit del form con SSE Stream (per ENDU) o REST (per FIDAL)
    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        hideError();

        const first = firstNameInput.value.trim();
        const last = lastNameInput.value.trim();
        const team = teamCodeInput.value.trim();
        const exactDate = exactDateInput ? exactDateInput.value.trim() : "";
        const eventName = eventNameInput ? eventNameInput.value.trim() : "";
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

        // --- MODALITÀ ARCHIVIO FIDAL ---
        if (currentMode === "fidal") {
            const fidalParams = new URLSearchParams();
            fidalParams.append("last_name", last);
            if (first) fidalParams.append("first_name", first);
            if (periodValue && periodValue.startsWith("year_")) {
                fidalParams.append("year", periodValue.replace("year_", ""));
            }
            if (eventName) fidalParams.append("city_or_race", eventName);

            progressPanel.classList.remove("hidden");
            progressTitle.textContent = "Ricerca scheda atleta su fidal.it...";
            progressCheckedText.textContent = "Consultazione graduatorie ufficiali...";
            progressMatchesText.textContent = "";
            progressBar.style.width = "75%";
            progressPercentage.textContent = "75%";

            fetch(`/api/fidal/search?${fidalParams.toString()}`)
                .then(async (res) => {
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || "Errore durante la ricerca FIDAL");
                    return data;
                })
                .then((data) => {
                    setScanningState(false);
                    progressBar.style.width = "100%";
                    progressPercentage.textContent = "100%";
                    setTimeout(() => progressPanel.classList.add("hidden"), 500);

                    if (!data.success || !data.athlete || !data.athlete.results || data.athlete.results.length === 0) {
                        emptyStateTitle.textContent = "Nessuna Gara Trovata su FIDAL";
                        emptyStateDesc.textContent = data.message || `Nessuna gara ufficiale FIDAL trovata per '${last}' con i filtri selezionati.`;
                        emptyState.classList.remove("hidden");
                        resultsHeader.classList.add("hidden");
                    } else {
                        renderFidalResults(data.athlete, data.elapsed_seconds);
                    }
                })
                .catch((err) => {
                    setScanningState(false);
                    progressPanel.classList.add("hidden");
                    showError(err.message || "Errore di connessione con l'archivio federale FIDAL.");
                });
            return;
        }

        // --- MODALITÀ TRAIL RUNNING (WEDOSPORT) ---
        if (currentMode === "trail") {
            const wedoParams = new URLSearchParams();
            wedoParams.append("last_name", last);
            if (first) wedoParams.append("first_name", first);
            if (periodValue && periodValue.startsWith("year_")) {
                wedoParams.append("year", periodValue.replace("year_", ""));
            }
            if (eventName) wedoParams.append("race_name", eventName);

            progressPanel.classList.remove("hidden");
            progressTitle.textContent = "Ricerca scheda atleta su Wedosport.net...";
            progressCheckedText.textContent = "Consultazione archivio storico Trail dal 2004...";
            progressMatchesText.textContent = "";
            progressBar.style.width = "75%";
            progressPercentage.textContent = "75%";

            fetch(`/api/wedosport/search?${wedoParams.toString()}`)
                .then(async (res) => {
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || "Errore durante la ricerca Wedosport");
                    return data;
                })
                .then((data) => {
                    setScanningState(false);
                    progressBar.style.width = "100%";
                    progressPercentage.textContent = "100%";
                    setTimeout(() => progressPanel.classList.add("hidden"), 500);

                    if (!data.success || !data.athlete || !data.athlete.results || data.athlete.results.length === 0) {
                        emptyStateTitle.textContent = "Nessuna Gara Trail Trovata su Wedosport";
                        emptyStateDesc.textContent = data.message || `Nessuna gara trail trovata per '${last}' nell'archivio Wedosport dal 2004 ad oggi.`;
                        emptyState.classList.remove("hidden");
                        resultsHeader.classList.add("hidden");
                    } else {
                        renderWedosportResults(data.athlete, data.elapsed_seconds, data.other_candidates);
                    }
                })
                .catch((err) => {
                    setScanningState(false);
                    progressPanel.classList.add("hidden");
                    showError(err.message || "Errore di connessione con l'archivio Wedosport.");
                });
            return;
        }

        // --- MODALITÀ GARE FUTURE E RISULTATI ENDU (SSE) ---
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
        if (exactDate) params.append("exact_date", exactDate);
        if (eventName) params.append("event_name", eventName);

        let streamUrl = "";
        if (currentMode === "future") {
            params.append("months", periodValue || "5");
            const platform = platformSelect ? platformSelect.value : "all";
            if (platform) params.append("platform", platform);
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
                const checked = packet.checked !== undefined ? packet.checked : (packet.scanned !== undefined ? packet.scanned : 0);
                const matches = packet.matches_count !== undefined ? packet.matches_count : (packet.matches !== undefined ? packet.matches : 0);
                const percent = packet.total > 0 ? Math.round((checked / packet.total) * 100) : 0;
                progressBar.style.width = `${percent}%`;
                progressPercentage.textContent = `${percent}%`;
                progressCheckedText.textContent = `${checked} / ${packet.total} gare verificate`;
                progressMatchesText.textContent = `${matches} ${matches === 1 ? 'gara trovata' : 'gare trovate'}`;
                if (packet.current_event && progressCurrentEvent) {
                    const srcBadge = packet.source ? `[${packet.source}] ` : "";
                    progressCurrentEvent.textContent = `${srcBadge}${packet.current_event}`;
                }
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
                    const exactDate = exactDateInput ? exactDateInput.value.trim() : "";
                    const eventName = eventNameInput ? eventNameInput.value.trim() : "";
                    let specificFilterNote = "";
                    if (exactDate && eventName) {
                        specificFilterNote = ` in data ${formatDateItalian(exactDate)} per la manifestazione "${eventName}"`;
                    } else if (exactDate) {
                        specificFilterNote = ` per la data specifica ${formatDateItalian(exactDate)}`;
                    } else if (eventName) {
                        specificFilterNote = ` per la manifestazione "${eventName}"`;
                    }

                    emptyStateTitle.textContent = currentMode === "future" 
                        ? "Nessuna Iscrizione Trovata"
                        : "Nessun Risultato in Classifica Trovato";
                    emptyStateDesc.textContent = currentMode === "future"
                        ? `Nessun atleta corrispondente ai criteri inseriti risulta iscritto${specificFilterNote || " a manifestazioni future nell'intervallo selezionato"}.`
                        : `Nessun risultato di gara trovato per l'atleta nelle classifiche ENDU${specificFilterNote || " dell'intervallo selezionato"}.`;
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

    function formatDateItalian(isoStr) {
        if (!isoStr) return "";
        const parts = isoStr.split("-");
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return isoStr;
    }

    function updateResultsCount(elapsed) {
        const count = foundMatches.length;
        const entity = currentMode === "future" ? "Gara Trovata" : "Gara con Risultati";
        const entities = currentMode === "future" ? "Gare Trovate" : "Gare con Risultati";
        resultsCountTitle.textContent = `${count} ${count === 1 ? entity : entities}`;
        
        const periodText = timePeriodSelect.options[timePeriodSelect.selectedIndex]?.text || "";
        const exactDate = exactDateInput ? exactDateInput.value.trim() : "";
        const eventName = eventNameInput ? eventNameInput.value.trim() : "";

        let filterDesc = periodText;
        if (exactDate && eventName) {
            filterDesc = `la data ${formatDateItalian(exactDate)} e gara "${eventName}"`;
        } else if (exactDate) {
            filterDesc = `la data ${formatDateItalian(exactDate)}`;
        } else if (eventName) {
            filterDesc = `la gara "${eventName}" (${periodText})`;
        }

        if (elapsed) {
            resultsSubTitle.textContent = `Scansione completata in ${elapsed}s su ${filterDesc}`;
        } else {
            resultsSubTitle.textContent = `Risultati aggiornati in tempo reale per ${filterDesc}`;
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
                <div class="flex items-center space-x-2 shrink-0">
                    <a href="${getStravaSearchUrl(ent.full_name)}" target="_blank" rel="noopener noreferrer" title="Cerca ${escapeHtml(ent.full_name)} su Strava"
                        class="px-2.5 py-1 rounded-lg bg-orange-50 hover:bg-orange-100 text-[#FC5200] border border-orange-200 text-xs font-semibold transition-colors flex items-center space-x-1 shadow-2xs">
                        <svg class="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7.01 13.828h4.172"/></svg>
                        <span>Cerca su Strava</span>
                    </a>
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

        const srcUpper = (match.source || "").toUpperCase();
        const isIcron = srcUpper === "ICRON";
        const isWedo = srcUpper === "WEDOSPORT";

        let sourceBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-emerald-100 text-emerald-900 border border-emerald-300 tracking-wider">ENDU</span>`;
        let verifyLabel = "Verifica ENDU";
        let verifyBtnClass = "px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold border border-emerald-200 transition-colors flex items-center space-x-1";

        if (isIcron) {
            sourceBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-amber-100 text-amber-900 border border-amber-300 tracking-wider">ICRON</span>`;
            verifyLabel = "Scheda ICRON";
            verifyBtnClass = "px-3 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-semibold border border-amber-300 transition-colors flex items-center space-x-1";
        } else if (isWedo) {
            sourceBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-stone-200 text-stone-900 border border-stone-400 tracking-wider flex items-center space-x-1"><i data-lucide="mountain" class="w-2.5 h-2.5 text-amber-800"></i><span>WEDOSPORT</span></span>`;
            verifyLabel = "Lista Wedosport";
            verifyBtnClass = "px-3 py-1.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-800 text-xs font-semibold border border-stone-300 transition-colors flex items-center space-x-1";
        }

        card.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div class="space-y-1.5">
                    <div class="flex items-center space-x-2">
                        ${sourceBadge}
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
                        class="${verifyBtnClass}">
                        <i data-lucide="${isIcron ? 'external-link' : 'check-circle'}" class="w-3.5 h-3.5"></i>
                        <span>${verifyLabel}</span>
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
                    <div class="flex items-center space-x-2 shrink-0">
                        <a href="${getStravaSearchUrl(res.full_name)}" target="_blank" rel="noopener noreferrer" title="Cerca ${escapeHtml(res.full_name)} su Strava"
                            class="px-2.5 py-1 rounded-lg bg-orange-50 hover:bg-orange-100 text-[#FC5200] border border-orange-200 text-xs font-semibold transition-colors flex items-center space-x-1 shadow-2xs">
                            <svg class="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7.01 13.828h4.172"/></svg>
                            <span>Cerca su Strava</span>
                        </a>
                        ${res.bib ? `
                            <div class="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md bg-amber-50 text-amber-900 border border-amber-300 text-xs">
                                <span class="text-[10px] uppercase font-bold text-amber-700">Pettorale</span>
                                <span class="font-mono font-bold">#${escapeHtml(res.bib)}</span>
                            </div>
                        ` : ''}
                    </div>
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

    // Render Risultati Ufficiali Carriera FIDAL
    function renderFidalResults(athlete, elapsed) {
        resultsContainer.innerHTML = "";
        foundMatches = athlete.results;

        const count = athlete.results.length;
        resultsCountTitle.textContent = `${count} ${count === 1 ? 'Gara Ufficiale Trovata' : 'Gare Ufficiali Trovate'}`;
        resultsSubTitle.textContent = `Carriera FIDAL estratta in ${elapsed}s per ${athlete.name} (${athlete.society})`;
        resultsHeader.classList.remove("hidden");
        emptyState.classList.add("hidden");

        // 1. Scheda Profilo Atleta
        const profileCard = document.createElement("div");
        profileCard.className = "bg-gradient-to-r from-slate-900 to-indigo-950 rounded-2xl p-6 text-white shadow-md space-y-4";
        
        let pbBadges = "";
        if (athlete.personal_bests && athlete.personal_bests.length > 0) {
            pbBadges = `
                <div class="pt-3 border-t border-slate-700/60">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">Primati Personali Ufficiali (FIDAL):</span>
                    <div class="flex flex-wrap gap-2">
                        ${athlete.personal_bests.map(pb => `
                            <span class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-xs">
                                <span class="text-slate-300 font-semibold">${escapeHtml(pb.event)}:</span>
                                <span class="font-bold font-mono text-emerald-400 text-sm">${escapeHtml(pb.time)}</span>
                                <span class="text-[11px] text-slate-400">(${escapeHtml(pb.city)} ${escapeHtml(pb.year)})</span>
                            </span>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        profileCard.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div class="space-y-1">
                    <div class="flex items-center space-x-2">
                        <span class="px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-bold text-xs uppercase border border-indigo-500/30">Scheda Atleta Federale</span>
                        ${athlete.birth_date ? `<span class="text-xs text-slate-400 font-medium">&bull; Nato il ${escapeHtml(athlete.birth_date)}</span>` : ''}
                    </div>
                    <h3 class="text-2xl font-black tracking-tight text-white">${escapeHtml(athlete.name)}</h3>
                    <p class="text-sm text-slate-300 font-medium">Società: <span class="text-emerald-300 font-bold">${escapeHtml(athlete.society)}</span></p>
                </div>
                <div class="shrink-0 flex items-center space-x-2">
                    <a href="${getStravaSearchUrl(athlete.name)}" target="_blank" rel="noopener noreferrer" title="Cerca ${escapeHtml(athlete.name)} su Strava"
                        class="px-3.5 py-2 rounded-xl bg-[#FC5200]/20 hover:bg-[#FC5200]/30 border border-[#FC5200]/40 text-orange-200 text-xs font-semibold flex items-center space-x-2 transition-all">
                        <svg class="w-3.5 h-3.5 fill-[#FC5200]" viewBox="0 0 24 24"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7.01 13.828h4.172"/></svg>
                        <span>Cerca su Strava</span>
                    </a>
                    <a href="${escapeHtml(athlete.fidal_url)}" target="_blank" rel="noopener noreferrer"
                        class="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white text-xs font-semibold flex items-center space-x-2 transition-all">
                        <i data-lucide="external-link" class="w-4 h-4"></i>
                        <span>Scheda Ufficiale su FIDAL.it</span>
                    </a>
                </div>
            </div>
            ${pbBadges}
        `;
        resultsContainer.appendChild(profileCard);

        // 2. Elenco Gare Ufficiali
        athlete.results.forEach(r => {
            const row = document.createElement("div");
            row.className = "bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-300 transition-all";

            row.innerHTML = `
                <div class="flex items-start sm:items-center space-x-4">
                    <div class="w-14 h-14 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-col items-center justify-center shrink-0">
                        <span class="text-[10px] font-bold uppercase text-emerald-800">${escapeHtml(r.date)}</span>
                        <span class="text-base font-black text-emerald-950 font-mono">${escapeHtml(String(r.year))}</span>
                    </div>
                    <div class="space-y-1">
                        <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                            <span class="font-bold text-slate-900 text-base">${escapeHtml(r.city)}</span>
                            <span class="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 text-xs font-bold border border-indigo-100">${escapeHtml(r.discipline)}</span>
                            ${r.category ? `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-xs font-semibold">${escapeHtml(r.category)}</span>` : ''}
                        </div>
                        <p class="text-xs text-slate-500">Piazzamento ufficiale: <strong class="text-slate-800">${escapeHtml(r.rank_cleaned || r.rank)}</strong></p>
                    </div>
                </div>

                <div class="flex items-center space-x-4 shrink-0 sm:text-right">
                    <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                        <span class="block text-[10px] uppercase font-bold text-slate-400">Tempo Ufficiale</span>
                        <span class="text-xl font-mono font-black text-emerald-600">${escapeHtml(r.time)}</span>
                    </div>
                </div>
            `;
            resultsContainer.appendChild(row);
        });

        lucide.createIcons();
    }

    // Render Risultati Ufficiali Carriera Trail Wedosport
    function renderWedosportResults(athlete, elapsed, otherCandidates) {
        resultsContainer.innerHTML = "";
        foundMatches = athlete.results;

        const count = athlete.results.length;
        resultsCountTitle.textContent = `${count} ${count === 1 ? 'Gara Trail Trovata' : 'Gare Trail Trovate'}`;
        resultsSubTitle.textContent = `Palmarès Wedosport estratto in ${elapsed}s per ${athlete.name}`;
        resultsHeader.classList.remove("hidden");
        emptyState.classList.add("hidden");

        // 1. Scheda Profilo Atleta Trail
        const profileCard = document.createElement("div");
        profileCard.className = "bg-gradient-to-r from-stone-900 via-amber-950 to-slate-900 rounded-2xl p-6 text-white shadow-md space-y-4";

        let otherNotice = "";
        if (otherCandidates && otherCandidates.length > 0) {
            otherNotice = `
                <div class="pt-3 border-t border-stone-700/60 text-xs text-stone-300 flex flex-wrap items-center gap-1.5">
                    <span class="font-bold text-amber-300">Altri atleti trovati:</span>
                    ${otherCandidates.map(c => `<span class="px-2 py-0.5 rounded bg-white/10 text-stone-200">${escapeHtml(c.name)} (${c.total_races} gare${c.birth_year ? ', anno ' + c.birth_year : ''})</span>`).join(" ")}
                </div>
            `;
        }

        profileCard.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div class="space-y-1">
                    <div class="flex items-center space-x-2">
                        <span class="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-bold text-xs uppercase border border-amber-500/30 flex items-center space-x-1">
                            <i data-lucide="mountain" class="w-3.5 h-3.5 text-amber-300"></i>
                            <span>Carriera Trail & SkyRunning (Wedosport)</span>
                        </span>
                        ${athlete.birth_year ? `<span class="text-xs text-stone-300 font-medium">&bull; Anno di nascita: ${escapeHtml(String(athlete.birth_year))}</span>` : ''}
                    </div>
                    <h3 class="text-2xl font-black tracking-tight text-white">${escapeHtml(athlete.name)}</h3>
                    ${athlete.society ? `<p class="text-sm text-stone-300 font-medium">Società: <span class="text-amber-300 font-bold">${escapeHtml(athlete.society)}</span></p>` : ''}
                </div>
                <div class="shrink-0 flex items-center space-x-2">
                    <a href="${getStravaSearchUrl(athlete.name)}" target="_blank" rel="noopener noreferrer" title="Cerca ${escapeHtml(athlete.name)} su Strava"
                        class="px-3.5 py-2 rounded-xl bg-[#FC5200]/20 hover:bg-[#FC5200]/30 border border-[#FC5200]/40 text-orange-200 text-xs font-semibold flex items-center space-x-1.5 transition-all">
                        <svg class="w-3.5 h-3.5 fill-[#FC5200]" viewBox="0 0 24 24"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7.01 13.828h4.172"/></svg>
                        <span>Cerca su Strava</span>
                    </a>
                    <div class="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-white text-xs font-bold text-center">
                        <span class="block text-[10px] text-amber-300 uppercase">Totale Gare</span>
                        <span class="text-xl font-mono text-white">${athlete.total_races}</span>
                    </div>
                </div>
            </div>
            ${otherNotice}
        `;
        resultsContainer.appendChild(profileCard);

        // 2. Elenco Gare Trail Disputate
        athlete.results.forEach(r => {
            const row = document.createElement("div");
            row.className = "bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-300 transition-all";

            const rankBadge = r.rank_cleaned ? `<strong class="text-slate-900">${escapeHtml(r.rank_cleaned)}</strong>` : '<span class="text-slate-400">Classificato</span>';

            row.innerHTML = `
                <div class="flex items-start sm:items-center space-x-4">
                    <div class="w-16 h-16 rounded-xl bg-amber-50 border border-amber-200 flex flex-col items-center justify-center shrink-0 text-center px-1">
                        <span class="text-[10px] font-bold uppercase text-amber-800 leading-tight">${escapeHtml(r.date.split('/')[0] + '/' + r.date.split('/')[1])}</span>
                        <span class="text-base font-black text-amber-950 font-mono leading-none">${escapeHtml(String(r.year || ''))}</span>
                    </div>
                    <div class="space-y-1">
                        <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                            <span class="font-bold text-slate-900 text-base">${escapeHtml(r.race_name)}</span>
                            <span class="px-2 py-0.5 rounded-md bg-stone-100 text-stone-800 text-xs font-bold border border-stone-200 flex items-center space-x-1">
                                <i data-lucide="mountain" class="w-3 h-3 text-amber-700"></i>
                                <span>${escapeHtml(r.sport)}</span>
                            </span>
                            ${r.distance_km ? `<span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-900 text-xs font-bold border border-amber-200">${escapeHtml(r.distance_km)}</span>` : ''}
                        </div>
                        ${r.distance_name ? `<p class="text-xs text-slate-600 font-medium">${escapeHtml(r.distance_name)}</p>` : ''}
                        <div class="text-xs text-slate-500 flex flex-wrap items-center gap-x-3">
                            <span>Piazzamento: ${rankBadge}</span>
                            ${r.team ? `<span>&bull; Società: <strong class="text-slate-700">${escapeHtml(r.team)}</strong></span>` : ''}
                        </div>
                    </div>
                </div>

                <div class="flex items-center space-x-3 shrink-0 sm:text-right">
                    <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 min-w-[100px] text-center">
                        <span class="block text-[10px] uppercase font-bold text-slate-400">Tempo Ufficiale</span>
                        <span class="text-lg font-mono font-black text-amber-700">${escapeHtml(r.time)}</span>
                    </div>
                    ${r.classifica_url ? `
                        <a href="${escapeHtml(r.classifica_url)}" target="_blank" rel="noopener noreferrer"
                            class="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-xs">
                            <i data-lucide="trophy" class="w-3.5 h-3.5 text-amber-700"></i>
                            <span class="hidden sm:inline">Classifica</span>
                        </a>
                    ` : ''}
                </div>
            `;
            resultsContainer.appendChild(row);
        });

        lucide.createIcons();
    }

    // Copia riepilogo testuale
    btnExport.addEventListener("click", () => {
        if (foundMatches.length === 0) return;

        let summary = "";
        if (currentMode === "fidal") {
            summary = `=== CARRIERA ATLETA FIDAL (fidal.it) ===\n`;
            summary += `Atleta: ${lastNameInput.value} ${firstNameInput.value || ''}\n`;
            summary += `Totale gare trovate: ${foundMatches.length}\n\n`;
            foundMatches.forEach((r, idx) => {
                summary += `${idx + 1}. [${r.full_date || r.date + '/' + r.year}] ${r.discipline} a ${r.city} - Tempo: ${r.time} - Piazzamento: ${r.rank_cleaned || r.rank} (${r.category})\n`;
            });
        } else if (currentMode === "trail") {
            summary = `=== CARRIERA TRAIL RUNNING (Wedosport.net) ===\n`;
            summary += `Atleta: ${lastNameInput.value} ${firstNameInput.value || ''}\n`;
            summary += `Totale gare trovate: ${foundMatches.length}\n\n`;
            foundMatches.forEach((r, idx) => {
                summary += `${idx + 1}. [${r.date}] ${r.race_name} (${r.distance_name || r.distance_km}) - Tempo: ${r.time} - Piazzamento: ${r.rank_cleaned || r.rank || '-'}\n`;
                if (r.team) summary += `   Società: ${r.team}\n`;
                if (r.classifica_url) summary += `   Classifica: ${r.classifica_url}\n`;
            });
        } else if (currentMode === "future") {
            summary = `=== ISCRIZIONI FUTURE (ENDU, ICRON & WEDOSPORT) ===\n`;
            summary += `Criteri: Nome: ${firstNameInput.value || '-'} | Cognome: ${lastNameInput.value || '-'} | Società: ${teamCodeInput.value || '-'}\n`;
            summary += `Totale manifestazioni trovate: ${foundMatches.length}\n\n`;

            foundMatches.forEach((ev, idx) => {
                const srcBadge = ev.source ? `[${ev.source}] ` : "";
                summary += `${idx + 1}. ${srcBadge}${ev.name} (${ev.date_formatted}) - ${ev.location_formatted}\n`;
                ev.entrants.forEach(ent => {
                    summary += `   • Atleta: ${ent.full_name}`;
                    if (ent.bib) summary += ` | Pettorale: #${ent.bib}`;
                    if (ent.team_name) summary += ` | Società: ${ent.team_name}`;
                    if (ent.course_name) summary += ` | Gara: ${ent.course_name}`;
                    summary += `\n`;
                });
                summary += `   Link verifica: ${ev.verify_url}\n\n`;
            });
        } else {
            summary = `=== RISULTATI STORICI GARE ENDU ===\n`;
            summary += `Criteri: Nome: ${firstNameInput.value || '-'} | Cognome: ${lastNameInput.value || '-'} | Società: ${teamCodeInput.value || '-'}\n`;
            summary += `Totale manifestazioni trovate: ${foundMatches.length}\n\n`;

            foundMatches.forEach((ev, idx) => {
                summary += `${idx + 1}. ${ev.name} (${ev.date_formatted}) - ${ev.location_formatted}\n`;
                ev.results.forEach(res => {
                    summary += `   • Gara: ${res.race_name} | Atleta: ${res.full_name}\n`;
                    summary += `     Tempo Ufficiale: ${res.official_time || '-'} | Posizione Assoluta: ${res.absolute_position ? res.absolute_position + '°' : '-'}\n`;
                    if (res.category_position) summary += `     Pos. Categoria (${res.category || ''}): ${res.category_position}°\n`;
                    if (res.team_name) summary += `     Società: ${res.team_name}\n`;
                });
                summary += `   Classifica ENDU: ${ev.results_url}\n\n`;
            });
        }

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

    // Supporto parametri URL per navigazione diretta (es. ?mode=fidal&last=Marchesan&first=Danny&auto=1)
    const urlParams = new URLSearchParams(window.location.search);
    const paramMode = urlParams.get("mode");
    const paramLast = urlParams.get("last") || urlParams.get("lastName");
    const paramFirst = urlParams.get("first") || urlParams.get("firstName");
    const paramAuto = urlParams.get("auto");

    if (paramMode && ["future", "results", "fidal", "trail"].includes(paramMode)) {
        setupMode(paramMode);
    }
    if (paramLast) lastNameInput.value = paramLast;
    if (paramFirst) firstNameInput.value = paramFirst;
    if (paramAuto === "1" || paramAuto === "true") {
        setTimeout(() => searchForm.dispatchEvent(new Event("submit")), 300);
    }

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
