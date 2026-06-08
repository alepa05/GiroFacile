# GiroFacile - V3.6.2.2

Gestionale per pianificazione giri consegna con priorità agli orari di scarico.

## Novità V3.6.2.2

- Nome definitivo del gestionale: GiroFacile.
- Rimosso riquadro Logistica SRL dalla sidebar.
- Rimossi i pulsanti Filtri rapidi e Oggi.
- Profilo Admin cliccabile con pannello profilo.
- Foto profilo, nome, email e password gestibili localmente nel browser.
- Tasto Stampa dettaglio fermate nel risultato giro.
- Stampa pulita solo della tabella fermate, senza sidebar e senza form.
- Mantiene la logica V3.2/V3.3 sugli orari di scarico e sullo storico giri.

## Avvio locale

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Apri:

```text
http://127.0.0.1:8000
```

Login:

```text
admin
admin123
```


## Fix V3.6.2.2

- Corretta sovrapposizione della schermata login dopo l'accesso.
