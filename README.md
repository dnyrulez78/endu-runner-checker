# 🏃 Runner Scanner (v3.3)

Applicazione desktop e web locale moderna, veloce e pulita (disponibile sia come **eseguibile standalone portatile per Windows (.exe)** a zero configurazione, sia come codice sorgente Python FastAPI + frontend HTML5/Tailwind CSS) progettata per podisti e appassionati per:
1. **Verificare a quali manifestazioni future di Corsa su Strada & Trail Running** (road running, trail, skyrunning) presenti su [ENDU](https://www.endu.net), [ICRON](https://www.icron.it) e [Wedosport](https://www.wedosport.net) un atleta risulta iscritto, con supporto a filtro unificato o per singola piattaforma.
2. **Consultare lo storico dei risultati e tempi di gara su ENDU**, con filtri mirati per data specifica e nome gara/città, con storico a ritroso fino a oltre 15 anni (dal 2010 ad oggi).
3. **Interrogare l'Archivio Carriera Ufficiale FIDAL & gare storiche TDS**, risolvendo il recupero di tutte le manifestazioni competitive certificate non presenti su ENDU (cronometrate da TDS, TDS-Live, SDAM, WinningTime, Icron), visualizzando la scheda atleta federale, la società di appartenenza e i Primati Personali (PB).
4. **Consultare la Carriera & Risultati Trail Running su Wedosport**, con accesso al palmarès completo di gare Trail, Ultra Trail, Skyrunning e Vertical dal **2004 ad oggi** (distanze, chilometri, tempi, piazzamenti e link alle classifiche ufficiali).
5. **Cercare rapidamente l'atleta su Strava**, tramite il pulsante scorciatoia dedicato presente accanto a ogni atleta trovato e nelle schede carriera per consultare il profilo pubblico e seguirlo (richiede login attivo su Strava).

<p align="center">
  <img src="assets/screenshot.png" alt="Anteprima Interfaccia Runner Scanner v3.3" width="900" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

---

## 🌟 Novità Versione 3.3 & Caratteristiche Principali

- **Versione Desktop Standalone Portable Windows (`RunnerScanner.exe`)**:
  - Applicazione a finestra autonoma nativa Windows (basata su Edge WebView2 integrato nel sistema operativo) pronta all'uso senza dover installare Python, Java o altre dipendenze.
  - Si avvia con un doppio clic, supporta il ridimensionamento a schermo intero e si arresta istantaneamente chiudendo la finestra con la classica **"X"** in alto a destra.
  - **Portatile & Nessun database permanente**: nessun file permanente creato nel registro di sistema; il recupero e l'elaborazione dei dati avvengono temporaneamente in memoria per la visualizzazione a schermo.
- **Pulsante Scorciatoia "Cerca su Strava"**:
  - Consente di aprire con un singolo clic la ricerca atleti ufficiale di Strava nel browser per verificare le attività pubbliche dei podisti.
  - Presente sia accanto al nome di ciascun atleta nelle gare future e passate, sia all'interno dei riquadri anagrafici ufficiali (FIDAL e Wedosport).
  - **Zero scraping & Tutela della privacy**: l'applicazione non interroga né memorizza dati da Strava; si tratta di una semplice scorciatoia di navigazione (deep link) per l'utente autenticato su Strava.
  <p align="center" style="margin-top: 8px; margin-bottom: 12px;">
    <img src="assets/strava_button.png" alt="Pulsante Cerca su Strava" width="160" style="border-radius: 6px;" />
  </p>
- **Integrazione Piattaforma Trail Running Wedosport**:
  - Scheda dedicata **Carriera Trail (Wedosport)** con archivio storico completo a partire dal **2004 ad oggi** (oltre 22 anni di manifestazioni off-road).
  - Scheda gara con dettagli completi: specialità (*Trail Running, Ultra Trail, Skyrunning, Vertical*), chilometraggio esatto, tempo finale, posizione assoluta e di genere, stato della prova e collegamento diretto alla graduatoria ufficiale Wedosport.
  - Verifica automatica delle **iscrizioni future alle gare Wedosport** nella scheda *Iscrizioni Future* (sia nella ricerca combinata che con filtro dedicato).
  - Badge cromatico distintivo ambra/montagna `WEDOSPORT` per identificare immediatamente gli eventi off-road.
- **Supporto Multi-Piattaforma Unificato (ENDU + ICRON + Wedosport)**:
  - Scansione parallela automatica delle manifestazioni presenti su **ENDU** (`endu.net`), **ICRON** (`icron.it`) e **Wedosport** (`wedosport.net`).
  - **Filtro Piattaforma a 4 Opzioni**: possibilità di selezionare *Tutte le piattaforme*, *Solo ENDU*, *Solo ICRON* oppure *Solo Wedosport (Trail)*.
- **Quattro Modalità con Schede Dedicate**:
  - **Iscrizioni Future**: Scansiona il calendario per verificare la presenza dell'atleta o della squadra su ENDU, ICRON e Wedosport.
  - **Risultati ENDU**: Cerca in quali gare su strada passate l'atleta ha tagliato il traguardo e mostra tempi ufficiali, real-time e piazzamenti.
  - **Archivio FIDAL / TDS**: Recupera la carriera agonistica federale certificata (Mezze Maratone, 10km, Maratone) e include tutte le manifestazioni cronometrate da **TDS**, **SDAM** o **WinningTime** fin dal 2010.
  - **Carriera Trail (Wedosport)**: Consulta l'intera carriera off-road (Trail, Ultra, Skyrunning) dal 2004 ad oggi.
- **Filtro Mirato per Nome Gara o Città**:
  - Consente di restringere la scansione a una singola manifestazione o località per interrogare unicamente le gare pertinenti in pochi secondi.
- **Filtro per Data Specifica**:
  - Possibilità di inserire il giorno esatto di una gara (es. `25/05/2024`) per verificare solo quell'evento.
- **Scheda Atleta Federale & Primati Personali (PB)**:
  - Nella scheda FIDAL/TDS vengono evidenziati categoria, società sportiva, anno di nascita e i record personali (PB) certificati su ogni distanza.
- **Nessun Login Richiesto**: L'accesso alle informazioni sui portali avviene su risorse pubblicamente consultabili.
- **Concorrenza Asincrona & Connessioni Controllate**: Chiamate parallele con `httpx` regolate da semafori `asyncio` (6-8 connessioni simultanee) e cache tecnica dei calendari per non sovraccaricare i server remoti.
- **Barra di Avanzamento Real-Time (SSE)**: La scansione trasmette aggiornamenti in tempo reale via Server-Sent Events; ogni risultato trovato compare all'istante a schermo.
- **Suite di Test Automatizzata**: 17 test integrati (`tests/test_api.py`) con copertura di tutti i provider e flussi di streaming.

---

## 📁 Struttura del Progetto

```text
C:\ENDU-Tool\
├── app.py                   # Entry point FastAPI e server web locale (v3.3)
├── desktop_app.py           # Entry point finestra desktop nativa (WebView2)
├── runner_scanner.spec      # Configurazione PyInstaller per bundling standalone
├── compila_exe.bat          # Script per generare RunnerScanner.exe con 1 clic
├── version_info.txt         # Metadati Windows PE dell'eseguibile (v3.3, copyright)
├── requirements.txt         # Dipendenze Python (fastapi, uvicorn, httpx, pywebview, cryptography)
├── avvia_app.bat            # Script di avvio rapido web nel browser (Windows)
├── LICENSE                  # Licenza per uso strettamente personale e privato
├── README.md                # Documentazione tecnica e condizioni d'uso
├── assets\
│   ├── icon.ico             # Icona applicazione Windows multi-risoluzione
│   ├── icon.png             # Logo e icona dell'applicazione ad alta risoluzione
│   ├── screenshot.png       # Screenshot dell'interfaccia utente a 4 schede
│   └── strava_button.png    # Dettaglio interfaccia del pulsante di ricerca Strava
├── backend\
│   ├── __init__.py
│   ├── endu_client.py       # Motore asincrono, cache in memoria e chiamate ad ENDU
│   ├── icron_client.py      # Client asincrono e parser verifica iscritti ICRON
│   ├── wedosport_client.py  # Client asincrono, archivio carriera e iscritti Wedosport Trail
│   ├── fidal_client.py      # Client archivio atleti FIDAL, TDS e primati personali
│   └── models.py            # Schemi dati Pydantic per validazione e tipizzazione
├── frontend\
│   ├── index.html           # Interfaccia grafica reattiva a 4 schede con selettore piattaforma
│   └── static\
│       ├── app.js           # Logica client-side, gestione SSE e render delle card
│       └── style.css        # Stili e animazioni personalizzate
└── tests\
    └── test_api.py          # Suite di 17 test automatizzati (ENDU, ICRON, Wedosport, FIDAL, SSE)
```

---

## 🚀 Guida all'Installazione e all'Avvio

Runner Scanner può essere eseguito in **due modalità alternative**:

### 📦 Metodo 1: Eseguibile Standalone Portatile (Consigliato per Windows)

Se desideri utilizzare Runner Scanner come applicazione autonoma senza configurare Python:

1. **Scarica `RunnerScanner.exe`**:
   - Scarica l'ultima release dalla sezione [Releases](https://github.com/dnyrulez78/runner-scanner/releases) di GitHub.
2. **Avvia il programma**:
   - Fai doppio clic su **`RunnerScanner.exe`**. Si aprirà la finestra desktop dell'applicazione.
3. **Caratteristiche**:
   - **Zero Requisiti**: non richiede l'installazione di Python né runtime esterni (funziona nativamente su qualsiasi PC con Windows 10 o Windows 11 tramite Edge WebView2 già integrato nel sistema).
   - **Portatile**: può essere posizionato in qualsiasi cartella locale o su una chiavetta USB.
   - **Chiusura Pulita**: chiudendo la finestra con la **"X"** in alto a destra, l'applicazione e il server interno si spengono all'istante liberando la memoria.

---

### 🐍 Metodo 2: Esecuzione da Codice Sorgente (Python)

Se desideri eseguire il codice sorgente o effettuare verifiche locali:

#### Prerequisito: Python 3.10+
Assicurati che Python sia installato con l'opzione `Add python.exe to PATH`.

#### Avvio rapido con doppio clic
Fai doppio clic sul file **`avvia_app.bat`**. Lo script installerà le dipendenze mancanti e aprirà il browser su:
👉 **`http://localhost:8000`**

#### Avvio manuale da Terminale
```powershell
# Installa le dipendenze
pip install -r requirements.txt

# Avvia l'interfaccia Web locale nel browser
python app.py

# Oppure avvia la finestra desktop nativa
python desktop_app.py
```

---

## 🎯 Come Eseguire una Ricerca

Nell'interfaccia puoi alternare tra quattro modalità tramite le schede in alto:

### 1. Scheda "Iscrizioni Future"
1. Inserisci il **Cognome** dell'atleta (obbligatorio per la consultazione personale) e facoltativamente il **Nome**.
2. **Società dell'atleta (filtro opzionale)**: per disambiguare atleti con lo stesso cognome o filtrare per squadra.
3. Seleziona l'orizzonte temporale desiderato (predefinito: **5 mesi**).
4. **Piattaforma**: seleziona se interrogare *Tutte le piattaforme*, *Solo ENDU*, *Solo ICRON* oppure *Solo Wedosport (Trail)*.
5. *(Opzionale)* Inserisci una data specifica o una parola chiave per la gara (es. `Foligno`, `Roma`).
6. Clicca su **Verifica Iscrizioni**: visualizzerai in tempo reale le manifestazioni a cui l'atleta risulta iscritto con il relativo pettorale assegnato e il badge della piattaforma.

### 2. Scheda "Risultati ENDU"
1. Inserisci il **Cognome** del podista.
2. Seleziona l'intervallo storico desiderato (*Ultimi 12 mesi*, *Ultimi 24 mesi*, o qualsiasi anno dal *2010* ad oggi).
3. *(Opzionale)* Inserisci il **Nome Gara o Città** per limitare la scansione ai soli eventi pertinenti e ottenere i risultati all'istante.
4. Clicca su **Cerca Risultati ENDU**: visualizzerai tutte le gare concluse con tempi ufficiali, real-time, piazzamenti e link alle classifiche ufficiali.

### 3. Scheda "Archivio FIDAL / TDS"
1. Inserisci il **Cognome** e facoltativamente il **Nome** dell'atleta.
2. *(Opzionale)* Filtra per anno solare o per città/gara.
3. Clicca su **Cerca Carriera FIDAL**:
   - Visualizzerai la **scheda ufficiale dell'atleta** con data di nascita, categoria e società di appartenenza.
   - Il riquadro **Primati Personali (PB)** certificati su 10km, Maratonina, Maratona.
   - L'elenco cronologico di tutte le gare ufficiali disputate, incluse le manifestazioni storiche cronometrate da **TDS**.

### 4. Scheda "Carriera Trail (Wedosport)"
1. Inserisci il **Cognome** e facoltativamente il **Nome** dell'atleta.
2. *(Opzionale)* Filtra per anno specifico dal 2004 ad oggi.
3. Clicca su **Cerca Trail Wedosport**:
   - Visualizzerai l'elenco cronologico di tutte le gare di **Trail Running, Ultra Trail, Skyrunning e Vertical** disputate.
   - Dettaglio con chilometraggio (`Km`), tempo impiegato, posizione assoluta e di genere, stato della gara e link diretto alla classifica ufficiale Wedosport.

### 5. Scorciatoia "Cerca su Strava"
In qualsiasi scheda, accanto a ciascun atleta individuato è presente il pulsante arancione **Cerca su Strava**:
- Facendo clic, si apre una nuova scheda del browser con la ricerca atleti su Strava pre-impostata col nominativo (`https://www.strava.com/athletes/search?text=...`).
- **Nota**: Per consultare i profili su Strava è necessario disporre di un account personale con sessione di login attiva su Strava nel proprio browser.

---

## ⚖️ Destinazione d'Uso, Condizioni e Tutela Privacy

### Destinazione d'Uso e Condizioni di Licenza

Runner Scanner è destinato **esclusivamente a persone fisiche per consultazioni personali e private** delle informazioni sportive disponibili sulle piattaforme sorgenti.

**Non è consentito** utilizzare il software nell’esercizio o a supporto di attività aziendali, professionali, associative o istituzionali, né per conto di aziende, società sportive, associazioni, enti o altre organizzazioni, anche senza scopo di lucro. L’appartenenza dell’utilizzatore a una società sportiva non impedisce l’uso strettamente personale; è categoricamente escluso l’uso nell’esercizio o a supporto di attività delle organizzazioni sopra indicate, anche se svolto da una persona fisica.

Non sono consentiti:
- raccolta massiva o sistematica di dati relativi ad atleti, oltre il recupero temporaneo necessario alla singola consultazione personale avviata dall'utilizzatore;
- creazione o aggiornamento di archivi, banche dati, elenchi o dossier su altre persone;
- monitoraggio ricorrente, programmato o continuativo delle iscrizioni e delle attività di terzi;
- utilizzo dei dati per marketing, selezione, profilazione, valutazione professionale o altre finalità organizzative;
- rivendita, cessione o pubblicazione di elenchi o profili ricavati tramite il software;
- esposizione del programma come servizio web accessibile a terzi o integrazione in servizi destinati alle organizzazioni.

Il recupero e l’elaborazione temporanei necessari alla singola consultazione personale rientrano nella funzione del programma. Non costituiscono autorizzazione a creare raccolte sistematiche o a diffondere i dati consultati.

Queste condizioni disciplinano l’utilizzo di Runner Scanner. Non attribuiscono diritti sui dati dei portali e non sostituiscono le condizioni d’uso delle piattaforme sorgenti o la normativa applicabile. L’utente deve rispettare eventuali limitazioni di accesso e non deve eludere protezioni o blocchi.

### Dati e Funzionamento Locale

- **Elaborazione temporanea**: Il programma recupera ed elabora temporaneamente le informazioni richieste per mostrarle sul dispositivo dell’utente. Non prevede un database applicativo permanente delle ricerche né un server centrale dell’autore per raccoglierle.
- **Interazione esterna**: Le richieste vengono inviate alle piattaforme interrogate. Aprendo un collegamento esterno si interagisce con il sito di destinazione; il pulsante «Cerca su Strava» invia a Strava il nominativo come parametro della ricerca, senza recuperare automaticamente profili o attività da Strava.
- **Tracce tecniche locali**: Browser, componenti di sistema, appunti, log o altri strumenti del dispositivo possono conservare tracce tecniche. Non viene garantita l’assenza assoluta di tracce su disco.
- **GDPR**: L’esclusione dal GDPR per attività esclusivamente personali o domestiche dipende dalle circostanze effettive dell’utilizzo e non è garantita dalla sola esecuzione locale del programma.

### Fonti, Marchi e Accuratezza

- Runner Scanner è un progetto indipendente, non affiliato, sponsorizzato o approvato da ENDU, ICRON, Wedosport, FIDAL, Strava o dagli altri servizi citati. Le denominazioni sono utilizzate per identificare le fonti o le destinazioni dei collegamenti. I relativi marchi appartengono ai rispettivi titolari.
- I risultati possono essere incompleti, non aggiornati o riferiti a omonimi. Verificare sempre le informazioni sul portale sorgente; l’assenza di un risultato non dimostra l'assenza di un’iscrizione.
- Il software è fornito "così com'è" senza garanzie ulteriori rispetto a quelle inderogabili previste dalla legge.

---

## 👤 Autore & Licenza

- **Autore**: [@dnyrulez78](https://github.com/dnyrulez78)
- **Licenza**: Codice sorgente disponibile con **Licenza per Uso Esclusivamente Personale e Privato** ([LICENSE](LICENSE)). È vietato qualsiasi uso aziendale, professionale, associativo o per conto di organizzazioni terze.
