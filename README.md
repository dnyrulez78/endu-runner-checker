# 🏃 ENDU Road Running Registration Checker

Applicazione web locale moderna, veloce e pulita (backend Python + frontend HTML5/Tailwind CSS) per verificare a quali manifestazioni future di **Corsa su Strada** (road running) presenti sulla piattaforma [ENDU](https://www.endu.net) un atleta o una società risulta iscritto.

---

## 🌟 Caratteristiche Principali

- **Orizzonte Temporale Flessibile**: Ricerca predefinita sui prossimi **5 mesi** (configurabile da 1 a 12 mesi).
- **Filtro Esclusivo Corsa su Strada**: Interroga unicamente le manifestazioni `discipline: road_running` escludendo automaticamente trail running, triathlon, ciclismo e nuoto.
- **Reverse Engineering API Native**: Comunica direttamente con gli endpoint nativi JSON di ENDU (`/api/events` e `/api/editions/{id}/entrants`), garantendo risposte immediate e zero overhead.
- **Alte Prestazioni & Nessun Blocco**: Chiamate asincrone concorrenti con `httpx` gestite da un `asyncio.Semaphore(8)` per verificare oltre 350 manifestazioni in meno di 4 secondi senza incorrere in rate limiting o blocchi 403.
- **Barra di Avanzamento Real-Time (SSE)**: La scansione trasmette aggiornamenti in tempo reale via Server-Sent Events; ogni gara trovata compare all'istante a schermo.
- **Caching Intelligente in Memoria**: Il calendario gare viene memorizzato per 1 ora in RAM, evitando di riscaricare centinaia di manifestazioni ad ogni singola ricerca.
- **Nessun Database Permanente**: Rispetta la privacy, non memorizza anagrafiche sul disco; le verifiche avvengono in diretta on-demand.
- **Riepilogo e Link Diretti**: Per ogni gara trovata mostra data, località, pettorale (se assegnato), categoria, società, distanza e link diretti sia alla pagina evento che alla pagina di verifica ufficiale ENDU.

---

## 📁 Struttura del Progetto

```text
C:\ENDU-Tool\
├── app.py                   # Entry point FastAPI e server web locale
├── requirements.txt         # Dipendenze Python (fastapi, uvicorn, httpx)
├── avvia_app.bat            # Script di avvio rapido con doppio clic (Windows)
├── README.md                # Documentazione e guida operativa
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

Nell'interfaccia web troverai un modulo pulito e intuitivo:

1. **Cognome** *(obbligatorio)*: es. `Rossi`, `Ferrari`, `Aiello`.
2. **Nome** *(opzionale)*: es. `Mario`, `Antonio`.
3. **Codice o Società** *(opzionale)*: 
   - Se inserisci sia il nome sia la società (es. `MI161` o `Canegrate`), il sistema verificherà l'atleta e filtrerà solo se appartiene a quella squadra.
   - Se lasci vuoti Nome e Cognome e inserisci solo la società, il sistema cercherà **tutti gli atleti** di quella squadra iscritti alle gare future!
4. **Orizzonte Temporale**: seleziona quanti mesi scansionare (predefinito: **5 mesi**).
5. Clicca su **Verifica Iscrizioni**:
   - Comparirà la barra di avanzamento che mostra in tempo reale le gare analizzate (es. `124 / 382 gare verificate`).
   - Non appena viene individuata un'iscrizione, la relativa card comparirà istantaneamente a schermo con il numero di pettorale (se già assegnato), la società, il percorso e i pulsanti per visualizzare l'evento su ENDU.
6. **Pulsante "Copia Risultati"**: permette di copiare con un clic il testo formattato dell'elenco gare trovate per incollarlo su WhatsApp, email o note.

---

## 🛡️ Note Tecniche sul Reverse Engineering di ENDU

- **Endpoint Calendario Eventi**:
  `GET https://www.endu.net/api/events?dateFrom={start}&dateTo={end}&discipline=road_running&pageSize=500&sort=date.from`
- **Endpoint Verifica Iscritti Manifestazione**:
  `GET https://www.endu.net/api/editions/{event_id}/entrants?firstName=...&lastName=...&teamCode=...`
- **Gestione Rate Limit**: L'uso di un semaforo a 8 connessioni contemporanee evita di saturare la connessione o generare allarmi lato server, garantendo al contempo una scansione completa di oltre 350 manifestazioni in appena 3-4 secondi.

---

## ⚖️ Disclaimer & Note Legali

- **Progetto Non Ufficiale**: Questo software è uno strumento indipendente open-source, sviluppato a scopo educativo, di studio e per **uso strettamente personale e domestico** (in conformità con l'Art. 2, par. 2, lett. c del Regolamento UE 2016/679 - GDPR).
- **Nessuna Affiliazione**: Il progetto non è in alcun modo affiliato, associato, sponsorizzato né approvato da **ENDU**, **Evodata S.r.l.** o da alcuna delle manifestazioni sportive e federazioni citate. Tutti i marchi, nomi di eventi e loghi appartengono ai rispettivi proprietari.
- **Nessuna Conservazione di Dati Personali**: L'applicazione opera esclusivamente "on-demand" in memoria RAM temporanea e non memorizza, raccoglie né archivia alcun dato anagrafico su database permanenti.
- **Responsabilità**: L'utente è l'unico responsabile dell'utilizzo dello strumento nel rispetto dei termini di servizio delle piattaforme terze interrogate.

---

## 👤 Autore & Licenza

- **Autore**: Danny ([@dnyrulez78](https://github.com/dnyrulez78) - [dnyrulez@gmail.com](mailto:dnyrulez@gmail.com))
- **Licenza**: Distribuito sotto licenza open-source [MIT](LICENSE). Sei libero di utilizzare, modificare e distribuire questo software citandone la paternità.

