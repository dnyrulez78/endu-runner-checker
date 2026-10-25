# 🏃 ENDU Road Running Checker & Results (v2.0)

Applicazione web locale moderna, veloce e pulita (backend Python + frontend HTML5/Tailwind CSS) per:
1. **Verificare a quali manifestazioni future di Corsa su Strada** (road running) presenti sulla piattaforma [ENDU](https://www.endu.net) un atleta o una società risulta iscritto.
2. **Consultare lo storico dei risultati e tempi di gara** ottenuti nelle manifestazioni passate (fino a 2 anni), con tempi ufficiali, real time, posizione assoluta e di categoria, distacchi e link alla classifica ufficiale.

<p align="center">
  <img src="assets/screenshot.png" alt="Anteprima Interfaccia ENDU Runner Scanner" width="900" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

---

## 🌟 Novità Versione 2.0 & Caratteristiche Principali

- **Doppia Modalità con Schede**:
  - **Iscrizioni Future**: Scansiona il calendario futuro per verificare la presenza dell'atleta o della squadra.
  - **Storico Risultati & Classifiche**: Cerca in quali gare passate l'atleta ha tagliato il traguardo e mostra i tempi ufficiali e i piazzamenti.
- **Nessun Login Richiesto**: L'accesso alle classifiche digitali ufficiali e alle liste iscritti avviene in modalità pubblica tramite le API native di ENDU.
- **Orizzonte Temporale Flessibile**:
  - *Gare future*: configurabile da 1 a 12 mesi (default 5 mesi).
  - *Storico risultati*: ultimi 3, 6, 12, 24 mesi o anno solare specifico (2026, 2025, 2024).
- **Filtro Esclusivo Corsa su Strada**: Interroga unicamente le manifestazioni `discipline: road_running` escludendo automaticamente trail running, triathlon, ciclismo e nuoto.
- **Alte Prestazioni & Nessun Blocco**: Chiamate asincrone concorrenti con `httpx` gestite da un `asyncio.Semaphore(8)` per verificare centinaia di manifestazioni in pochissimi secondi.
- **Barra di Avanzamento Real-Time (SSE)**: La scansione trasmette aggiornamenti in tempo reale via Server-Sent Events; ogni risultato trovato compare all'istante a schermo.
- **Caching Intelligente in Memoria**: Il calendario viene memorizzato temporaneamente in RAM per evitare chiamate ridondanti.
- **Nessun Database Permanente**: Rispetta la privacy, non memorizza anagrafiche sul disco; le verifiche avvengono in diretta on-demand.
- **Dettagli Completi e Link Diretti**: Visualizza data, località, pettorale, tempo ufficiale, real time, posizione assoluta, categoria, genere, distacco e link diretti sia alla pagina evento che alla classifica ufficiale ENDU.

---

## 📁 Struttura del Progetto

```text
C:\ENDU-Tool\
├── app.py                   # Entry point FastAPI e server web locale
├── requirements.txt         # Dipendenze Python (fastapi, uvicorn, httpx)
├── avvia_app.bat            # Script di avvio rapido con doppio clic (Windows)
├── README.md                # Documentazione e guida operativa
├── assets\
│   └── screenshot.png       # Screenshot dell'interfaccia utente
├── backend\
│   ├── __init__.py
│   ├── endu_client.py       # Motore asincrono, cache in memoria e chiamate ad ENDU
│   └── models.py            # Schemi dati Pydantic per validazione e tipizzazione
├── frontend\
│   ├── index.html           # Interfaccia grafica moderna e reattiva
│   └── static\
│       ├── app.js           # Logica client-side, gestione SSE e render delle card
│       └── style.css        # Stili e animazioni personalizzate
└── tests\
    └── test_api.py          # Suite di test automatizzati degli endpoint
```

---

## 🚀 Guida Passo-Passo per l'Installazione e l'Avvio

Poiché non hai esperienza di programmazione, segui questi semplici passaggi numerati a prova di errore:

### Metodo 1: Avvio Rapido con Doppio Clic (Consigliato su Windows)

1. Apri la cartella `C:\ENDU-Tool`.
2. Fai **doppio clic** sul file **`avvia_app.bat`**.
3. Il file verificherà automaticamente la presenza di Python, installerà le librerie mancanti e avvierà il server.
4. Apri il browser web (Chrome, Edge, Firefox, Brave) all'indirizzo:
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
🏃  ENDU ROAD RUNNING CHECKER  🏃
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

Nell'interfaccia web puoi alternare tra due modalità tramite le schede in alto:

### 1. Scheda "Iscrizioni Future"
1. Inserisci il **Cognome** (obbligatorio, es. `Rossi`, `Aiello`) e facoltativamente il **Nome**.
2. **Codice o Società (opzionale)**: per filtrare la squadra o cercare tutti gli atleti del team.
3. Seleziona l'orizzonte temporale (predefinito: **5 mesi**).
4. Clicca su **Verifica Iscrizioni**: visualizzerai in tempo reale le manifestazioni a cui l'atleta risulta iscritto con il relativo pettorale assegnato.

### 2. Scheda "Storico Risultati & Tempi" (Novità v2.0)
1. Inserisci il **Cognome** e/o il **Nome** del podista.
2. Seleziona l'intervallo storico desiderato (es. *Ultimi 12 mesi*, *Ultimi 24 mesi*, o anno solare *2025*, *2024*).
3. Clicca su **Cerca Risultati Storici**: visualizzerai tutte le gare concluse dall'atleta con:
   - **Tempo ufficiale e Real time**
   - **Posizione assoluta** all'arrivo
   - **Posizione di categoria e di genere**
   - **Distacco dal primo classificato**
   - Link diretto alla **classifica ufficiale ENDU** per consultare intertempi e graduatorie complete.

---

## 🛡️ Note Tecniche sul Reverse Engineering di ENDU

- **Endpoint Calendario Eventi**:
  `GET https://www.endu.net/api/events?dateFrom={start}&dateTo={end}&discipline=road_running&pageSize=500&sort=date.from`
- **Endpoint Verifica Iscritti Manifestazione**:
  `GET https://www.endu.net/api/editions/{event_id}/entrants?firstName=...&lastName=...&teamCode=...`
- **Endpoint Classifiche e Risultati Ufficiali**:
  - Impostazioni gara: `GET https://www.endu.net/api/results/events/{event_id}/settings`
  - Risultati atleti: `GET https://www.endu.net/api/results?editionId={edition_id}&raceId={race_id}&categoryId={cat_id}&optionId={opt_id}&searchText={search_text}`
- **Gestione Rate Limit**: L'uso di un semaforo a 8 connessioni contemporanee evita di saturare la connessione o generare allarmi lato server, garantendo una scansione ad alte prestazioni in pochi secondi.

---

## ⚖️ Disclaimer & Note Legali

- **Progetto Non Ufficiale**: Questo software è uno strumento indipendente open-source, sviluppato a scopo educativo, di studio e per **uso strettamente personale e domestico** (in conformità con l'Art. 2, par. 2, lett. c del Regolamento UE 2016/679 - GDPR).
- **Nessuna Affiliazione**: Il progetto non è in alcun modo affiliato, associato, sponsorizzato né approvato da **ENDU**, **Evodata S.r.l.** o da alcuna delle manifestazioni sportive e federazioni citate. Tutti i marchi, nomi di eventi e loghi appartengono ai rispettivi proprietari.
- **Nessuna Conservazione di Dati Personali**: L'applicazione opera esclusivamente "on-demand" in memoria RAM temporanea e non memorizza, raccoglie né archivia alcun dato anagrafico su database permanenti.
- **Responsabilità**: L'utente è l'unico responsabile dell'utilizzo dello strumento nel rispetto dei termini di servizio delle piattaforme terze interrogate.

---

## 👤 Autore & Licenza

- **Autore**: [@dnyrulez78](https://github.com/dnyrulez78)
- **Licenza**: Distribuito sotto licenza open-source [MIT](LICENSE). Sei libero di utilizzare, modificare e distribuire questo software citandone la paternità.

