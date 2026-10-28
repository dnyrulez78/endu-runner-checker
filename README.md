# 🏃 ENDU & ICRON Road Running Checker, Results & FIDAL/TDS Archive (v3.1)

Applicazione web locale moderna, veloce e pulita (backend Python + frontend HTML5/Tailwind CSS) per:
1. **Verificare a quali manifestazioni future di Corsa su Strada** (road running) presenti su [ENDU](https://www.endu.net) e su [ICRON](https://www.icron.it) un atleta o una società risulta iscritto, con supporto a filtro unificato o per singola piattaforma.
2. **Consultare lo storico dei risultati e tempi di gara su ENDU**, con filtri mirati per data specifica e nome gara/città, con storico a ritroso fino a oltre 10 anni (dal 2010 ad oggi).
3. **Interrogare l'Archivio Carriera Ufficiale FIDAL & gare storiche TDS**, risolvendo il recupero di tutte le manifestazioni non presenti su ENDU (cronometrate da TDS, TDS-Live, SDAM, WinningTime, Icron), visualizzando la scheda atleta federale, la società di appartenenza e i Primati Personali (PB).

<p align="center">
  <img src="assets/screenshot.png" alt="Anteprima Interfaccia ENDU & ICRON Runner Scanner v3.1" width="900" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

---

## 🌟 Novità Versione 3.1 & Caratteristiche Principali

- **Supporto Multi-Piattaforma: ENDU + ICRON (Novità v3.1)**:
  - Scansione parallela automatica delle manifestazioni presenti su **ICRON** (`icron.it`) oltre che su **ENDU** (`endu.net`).
  - Interroga direttamente gli eventi podistici ICRON (es. *iRun21 La Mezza di Vicenza*, *Due Mari Marathon*, ecc.).
  - Funzione "Verifica Iscrizioni" con supporto automatico sia ai cognomi sia ai **codici società FIDAL** (es. `vi654` convertito lato server in *Vicenza Runners*).
  - **Filtro Piattaforma Dedicato**: possibilità di scegliere se cercare su *Tutte (ENDU + ICRON)*, *Solo ENDU* oppure *Solo ICRON*.
  - Badge cromatici distintivi nelle card dei risultati (smeraldo per ENDU, ambra per ICRON) con link diretti alla pagina evento ufficiale.
- **Tripla Modalità con Schede Dedicate**:
  - **Iscrizioni Future**: Scansiona il calendario futuro per verificare la presenza dell'atleta o della squadra su ENDU e ICRON.
  - **Risultati ENDU**: Cerca in quali gare passate l'atleta ha tagliato il traguardo e mostra i tempi ufficiali e i piazzamenti.
  - **Archivio FIDAL / TDS**: Recupera la carriera agonistica ufficiale dell'atleta (Mezze Maratone, 10km, Maratone) e include tutte le manifestazioni cronometrate da **TDS**, **SDAM** o **WinningTime** fin dal 2010.
- **Filtro Mirato per Nome Gara o Città**:
  - Consente di restringere la scansione a una singola manifestazione o località (es. digitando `jesolo` o `vicenza` vengono scansionate solo le gare pertinenti in 1-2 secondi anziché centinaia di eventi).
- **Filtro per Data Specifica**:
  - Possibilità di inserire il giorno esatto di una gara (es. `25/05/2024`) per interrogare unicamente quell'evento.
- **Archivio Storico Esteso fino al 2010**:
  - Ricerca a ritroso fino a 15 anni per consultare qualsiasi edizione passata su ENDU e FIDAL.
- **Scheda Atleta Federale & Primati Personali (PB)**:
  - Nella scheda FIDAL/TDS vengono evidenziati categoria, società sportiva, anno di nascita e i record personali (PB) certificati su ogni distanza.
- **Nessun Login Richiesto**: L'accesso ai risultati digitali ufficiali e alle liste iscritti di ENDU e ICRON avviene in modalità pubblica on-demand.
- **Filtro Esclusivo Corsa su Strada**: Interroga unicamente le manifestazioni `road_running` escludendo automaticamente trail, triathlon, ciclismo e nuoto.
- **Alte Prestazioni & Concorrenza Asincrona**: Chiamate parallele con `httpx` gestite da semafori `asyncio` per verificare centinaia di manifestazioni in pochi secondi senza bloccare l'interfaccia.
- **Barra di Avanzamento Real-Time (SSE)**: La scansione trasmette aggiornamenti in tempo reale via Server-Sent Events; ogni risultato trovato compare all'istante a schermo.
- **Caching Intelligente in Memoria**: I calendari ENDU e ICRON vengono memorizzati temporaneamente in RAM per evitare chiamate ridondanti.
- **Privacy & Nessun Database Permanente**: Rispetta la privacy, non memorizza anagrafiche sul disco; le verifiche avvengono in diretta on-demand.
- **Esportazione Risultati**: Pulsante rapido per copiare il riepilogo testuale formattato degli arrivi o degli iscritti negli appunti.

---

## 📁 Struttura del Progetto

```text
C:\ENDU-Tool\
├── app.py                   # Entry point FastAPI e server web locale (v3.1)
├── requirements.txt         # Dipendenze Python (fastapi, uvicorn, httpx)
├── avvia_app.bat            # Script di avvio rapido con doppio clic (Windows)
├── README.md                # Documentazione e guida operativa
├── assets\
│   └── screenshot.png       # Screenshot aggiornato dell'interfaccia utente
├── backend\
│   ├── __init__.py
│   ├── endu_client.py       # Motore asincrono, cache in memoria e chiamate ad ENDU
│   ├── icron_client.py      # Client asincrono e parser verifica iscritti ICRON
│   ├── fidal_client.py      # Client archivio atleti FIDAL, TDS e primati personali
│   └── models.py            # Schemi dati Pydantic per validazione e tipizzazione
├── frontend\
│   ├── index.html           # Interfaccia grafica reattiva a 3 schede con selettore piattaforma
│   └── static\
│       ├── app.js           # Logica client-side, gestione SSE e render delle card
│       └── style.css        # Stili e animazioni personalizzate
└── tests\
    └── test_api.py          # Suite di 14 test automatizzati (ENDU, ICRON, FIDAL, SSE)
```

---

## 🚀 Guida Passo-Passo per l'Installazione e l'Avvio

### ⚠️ Prerequisito su un Nuovo PC (Una tantum)
Se stai aprendo il progetto su un computer dove **Python non è ancora presente**:
1. Scarica Python dal sito ufficiale: 👉 [python.org/downloads](https://www.python.org/downloads/) (consigliato Python 3.11 o 3.12).
2. **FONDAMENTALE**: Nella primissima schermata dell'installazione, spunta la casella in basso:
   **`[X] Add python.exe to PATH`**
3. Clicca su **Install Now** e attendi il completamento.
*(Se ti dimentichi questo passaggio, `avvia_app.bat` ti guiderà automaticamente aprendoti la pagina corretta).*

---

### Metodo 1: Avvio Rapido con Doppio Clic (Consigliato su Windows)

1. Apri la cartella del progetto (es. `C:\ENDU-Tool` oppure la cartella decompressa dallo ZIP).
2. Fai **doppio clic** sul file **`avvia_app.bat`**.
3. Lo script rileverà automaticamente Python, installerà le librerie necessarie (`fastapi`, `uvicorn`, `httpx`) e aprirà direttamente il browser su:
   👉 **`http://localhost:8000`**

---

### Metodo 2: Avvio Manuale da Terminale (PowerShell o Prompt dei Comandi)

#### Passo 1: Apri il Terminale nella cartella del progetto
1. Premi il tasto `Windows + R`, digita `powershell` (o `cmd`) e premi **Invio**.
2. Spostati nella cartella del progetto digitando:
   ```powershell
   cd C:\ENDU-Tool
   ```

#### Passo 2: Installa le librerie necessarie
Digita il seguente comando e premi **Invio**:
```powershell
pip install -r requirements.txt
```
*(Le librerie richieste sono solo 3: `fastapi`, `uvicorn`, `httpx`)*.

#### Passo 3: Avvia l'applicazione
Digita il comando di avvio e premi **Invio**:
```powershell
python app.py
```

Vedrai comparire a schermo un messaggio simile a:
```text
============================================================
🏃  ENDU & ICRON ROAD RUNNING CHECKER  🏃
============================================================
Server locale avviato con successo!
Apri il tuo browser all'indirizzo: http://127.0.0.1:8000
Premi CTRL+C per arrestare il server.
============================================================
```

#### Passo 4: Utilizza l'applicazione nel Browser
Apri il tuo browser preferito e vai su:
👉 **`http://localhost:8000`**

---

## 🎯 Come Eseguire una Ricerca

Nell'interfaccia web puoi alternare tra tre modalità tramite le schede in alto:

### 1. Scheda "Iscrizioni Future"
1. Inserisci il **Cognome** (obbligatorio, es. `Rossi`, `Marchesan`, `Aiello`) e facoltativamente il **Nome**.
2. **Codice o Società (opzionale)**: per filtrare la squadra (es. `vi654` o `Vicenza Runners`) o cercare tutti gli atleti del team.
3. Seleziona l'orizzonte temporale (predefinito: **5 mesi**).
4. **Piattaforma (Novità v3.1)**: seleziona se interrogare *Tutte (ENDU + ICRON)*, *Solo ENDU* oppure *Solo ICRON*.
5. *(Opzionale)* Inserisci una data specifica o una parola chiave per la gara (es. `Vicenza` o `Foligno`).
6. Clicca su **Verifica Iscrizioni**: visualizzerai in tempo reale le manifestazioni a cui l'atleta risulta iscritto con il relativo pettorale assegnato e il badge della piattaforma.

### 2. Scheda "Risultati ENDU"
1. Inserisci il **Cognome** e/o il **Nome** del podista.
2. Seleziona l'intervallo storico desiderato (es. *Ultimi 12 mesi*, *Ultimi 24 mesi*, o qualsiasi anno dal *2010* al *2026*).
3. *(Opzionale ma consigliato)* Inserisci il **Nome Gara o Città** (es. `Jesolo`) per limitare la scansione ai soli eventi pertinenti e ottenere i risultati all'istante.
4. Clicca su **Cerca Risultati Storici**: visualizzerai tutte le gare concluse dall'atleta con:
   - **Tempo ufficiale e Real time**
   - **Posizione assoluta** all'arrivo
   - **Posizione di categoria e di genere**
   - **Distacco dal primo classificato**
   - Link diretto alla **classifica ufficiale ENDU** per consultare intertempi e graduatorie complete.

### 3. Scheda "Archivio FIDAL / TDS"
1. Inserisci il **Cognome** (es. `Marchesan`) e facoltativamente il **Nome** (es. `Danny`).
2. *(Opzionale)* Filtra per anno solare o per città/gara.
3. Clicca su **Consulta Archivio FIDAL / TDS**:
   - Visualizzerai la **scheda ufficiale dell'atleta** con data di nascita, categoria e società di tesseramento.
   - Il box **Primati Personali (PB)** certificati su 10km, Maratonina, Maratona.
   - L'elenco cronologico di tutte le gare ufficiali disputate, incluse le gare cronometrate da **TDS** (come le storiche mezze maratone di Vicenza o Cittadella) che non sono reperibili su ENDU.
   - Link diretto alla scheda atleta sul portale federale `fidal.it`.

---

## 🛡️ Note Tecniche sulle Sorgenti Dati

- **API Calendario Eventi ENDU**:
  `GET https://www.endu.net/api/events?dateFrom={start}&dateTo={end}&discipline=road_running&pageSize=500&sort=date.from`
- **API Iscritti ENDU**:
  `GET https://www.endu.net/api/editions/{event_id}/entrants?firstName=...&lastName=...&teamCode=...`
- **API Risultati ENDU**:
  - Settings gara: `GET https://www.endu.net/api/results/events/{event_id}/settings`
  - Risultati atleti: `GET https://www.endu.net/api/results?editionId={edition_id}&raceId={race_id}&categoryId={cat_id}&optionId={opt_id}&searchText={search_text}`
- **API Manifestazioni & Iscritti ICRON (Novità v3.1)**:
  - Calendario manifestazioni: `POST https://www.icron.it/IcronNewGO/getOpenEvents` (filtrato per disciplina running e road racing)
  - Verifica iscritti per atleta o codice società: `POST https://www.icron.it/IcronNewGO/getIscrizioni` con parametro mirato `criterio` (`squadra:{code}` o `cognome:{last}`), garantendo accesso pubblico trasparente senza autenticazione anche su gare con elenco generale protetto.
- **Archivio Federale FIDAL & TDS**:
  - Ricerca anagrafica: `POST https://www.fidal.it/result.php` con parametro `cerca`
  - Estrazione profilo e graduatorie: analisi diretta asincrona della scheda atleta ufficiale `https://www.fidal.it/atleta/{slug}/{hash}` senza dipendenze esterne pesanti.
- **Gestione Concorrenza & Rate Limit**: Semafori asincroni con `httpx` limitati per garantire velocità senza saturare le risorse di rete.

---

## ⚖️ Disclaimer & Note Legali

- **Progetto Non Ufficiale**: Questo software è uno strumento indipendente open-source, sviluppato a scopo educativo, di studio e per **uso strettamente personale e domestico** (in conformità con l'Art. 2, par. 2, lett. c del Regolamento UE 2016/679 - GDPR).
- **Nessuna Affiliazione**: Il progetto non è in alcun modo affiliato, associato, sponsorizzato né approvato da **ENDU**, **Evodata S.r.l.**, da **ICRON**, da **FIDAL** (Federazione Italiana di Atletica Leggera) o dalle società di cronometraggio citate (TDS, SDAM, WinningTime). Tutti i marchi, loghi e denominazioni appartengono ai rispettivi proprietari.
- **Nessuna Conservazione di Dati Personali**: L'applicazione opera esclusivamente "on-demand" in memoria volatile (RAM) e non memorizza né redistribuisce alcun dato anagrafico su database permanenti.
- **Responsabilità**: L'utente è l'unico responsabile dell'utilizzo dello strumento nel rispetto dei termini di servizio delle piattaforme terze interrogate.

---

## 👤 Autore & Licenza

- **Autore**: [@dnyrulez78](https://github.com/dnyrulez78)
- **Licenza**: Distribuito sotto licenza open-source [MIT](LICENSE). Sei libero di utilizzare, modificare e distribuire questo software citandone la paternità.
