import math, os, time, requests
from urllib.parse import quote

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org").rstrip("/")
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")

# V3.2 - Motore percorso con priorità alle finestre orarie di scarico.
# Logica principale:
# 1) prima cerca consegne fattibili nella fascia oraria;
# 2) se arriva prima, calcola attesa;
# 3) se una consegna rischia di chiudere, la anticipa;
# 4) distanza e velocità vengono considerate solo dopo la fattibilità oraria;
# 5) segnala "Non fattibile" solo quando non riesce davvero a rispettare gli orari.

def parse_hhmm(value):
    if not value:
        return None
    try:
        h, m = str(value).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None

def fmt_hhmm(total_min):
    total_min = int(round(total_min)) % (24 * 60)
    return f"{total_min // 60:02d}:{total_min % 60:02d}"

def delivery_windows(d):
    """Restituisce le finestre orarie valide ordinate: [(start_min, end_min), ...]."""
    out = []

    a = parse_hhmm(d.get("scarico_mattina_da"))
    b = parse_hhmm(d.get("scarico_mattina_a"))
    if a is not None and b is not None and b > a:
        out.append((a, b))

    a = parse_hhmm(d.get("scarico_pomeriggio_da"))
    b = parse_hhmm(d.get("scarico_pomeriggio_a"))
    if a is not None and b is not None and b > a:
        out.append((a, b))

    return sorted(out)

def haversine_km(a, b):
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))

def geocode(address):
    r = requests.get(
        f"{NOMINATIM_URL}/search",
        params={"format": "json", "limit": 1, "q": address},
        headers={"User-Agent": "ToolConsegneAziendale/3.2"},
        timeout=15
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"Indirizzo non trovato: {address}")
    return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}

def osrm_route(a, b):
    try:
        r = requests.get(
            f"{OSRM_URL}/route/v1/driving/{a['lon']},{a['lat']};{b['lon']},{b['lat']}",
            params={"overview": "false"},
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        if data.get("routes"):
            route = data["routes"][0]
            return {"km": route["distance"] / 1000, "min": route["duration"] / 60}
    except Exception:
        pass

    # Fallback: stima semplice se OSRM non risponde.
    km = haversine_km(a, b) * 1.25
    return {"km": km, "min": (km / 45) * 60}

def build_google_maps_url(depot_address, deliveries, return_depot):
    stops = [depot_address] + [d["indirizzo"] for d in deliveries]
    if return_depot:
        stops.append(depot_address)
    return "https://www.google.com/maps/dir/" + "/".join(quote(x) for x in stops)

def evaluate_candidate(current_clock, leg, d):
    """
    Valuta una possibile prossima consegna.

    Ritorna:
    {
      feasible: bool,
      score: float,
      service_start: minuti assoluti del giorno,
      wait: minuti attesa,
      warning: testo,
      window_end: fine finestra usata o None
    }
    """
    travel_arrival = current_clock + leg["min"]
    service_min = float(d.get("tempo_scarico_min") or 0)
    windows = delivery_windows(d)

    # Se il cliente non ha finestre orarie, lo considero sempre fattibile.
    if not windows:
        return {
            "feasible": True,
            "score": leg["min"] + leg["km"] * 1.15,
            "service_start": travel_arrival,
            "wait": 0,
            "warning": "",
            "window_end": None,
        }

    best = None

    for start, end in windows:
        # Caso 1: arrivo prima dell'apertura -> posso aspettare.
        if travel_arrival < start:
            service_start = start
            wait = start - travel_arrival
            service_end = service_start + service_min
            feasible = service_end <= end
            slack = max(0, end - service_end)
            window_width = end - start

            if feasible:
                warning = f"Arrivo prima dell'apertura: attesa {int(round(wait))} min" if wait > 0 else ""
                # Score: finestre orarie prima, distanza dopo.
                # - attesa: costa, ma è accettabile
                # - slack basso: cliente rischia di chiudere, quindi va anticipato
                # - finestra stretta: va gestita prima
                score = (
                    wait * 1.6
                    + leg["min"] * 0.85
                    + leg["km"] * 1.05
                    + slack * 0.08
                    + window_width * 0.03
                )
            else:
                # Anche aspettando, lo scarico finirebbe dopo chiusura.
                late = service_end - end
                warning = "Scarico non completabile entro la fascia oraria"
                score = 50000 + late * 20 + leg["min"] + leg["km"]

        # Caso 2: arrivo durante la fascia.
        elif start <= travel_arrival <= end:
            service_start = travel_arrival
            wait = 0
            service_end = service_start + service_min
            feasible = service_end <= end
            slack = max(0, end - service_end)
            window_width = end - start

            if feasible:
                warning = ""
                # Cliente già aperto: molto preferibile.
                # Se sta per chiudere, lo score rimane basso per farlo prima.
                score = (
                    leg["min"] * 0.75
                    + leg["km"] * 1.0
                    + slack * 0.10
                    + window_width * 0.025
                )
            else:
                late = service_end - end
                warning = "Scarico terminerebbe dopo la chiusura"
                score = 40000 + late * 25 + leg["min"] + leg["km"]

        # Caso 3: sono già oltre questa fascia: provo la prossima.
        else:
            continue

        candidate = {
            "feasible": feasible,
            "score": score,
            "service_start": service_start,
            "wait": wait,
            "warning": warning,
            "window_end": end,
        }

        if best is None or candidate["score"] < best["score"]:
            best = candidate

    # Se nessuna fascia futura è utile, il cliente è non fattibile con l'orario attuale.
    if best is None:
        last_end = max(end for _, end in windows)
        late = max(0, travel_arrival - last_end)
        best = {
            "feasible": False,
            "score": 90000 + late * 30 + leg["min"] + leg["km"],
            "service_start": travel_arrival,
            "wait": 0,
            "warning": "Non fattibile: arrivo dopo le fasce orarie di scarico",
            "window_end": last_end,
        }

    # Piccola priorità a consegne pesanti/colli, ma solo dopo la fattibilità oraria.
    best["score"] -= float(d.get("peso_kg") or 0) * 0.01
    best["score"] -= float(d.get("colli") or 0) * 0.03

    return best

def optimize_route(depot_address, deliveries, vehicle=None, return_depot=True, start_time="08:00"):
    depot_coord = geocode(depot_address)

    for d in deliveries:
        d["coord"] = geocode(d["indirizzo"])
        time.sleep(1.05)

    remaining = deliveries[:]
    current = depot_coord
    ordered = []
    total_km = 0.0
    start_clock = parse_hhmm(start_time) or 8 * 60
    current_clock = start_clock

    while remaining:
        best_idx = 0
        best_score = None
        best_leg = None
        best_eval = None

        # Valuto tutte le consegne rimanenti e scelgo quella più intelligente,
        # non semplicemente quella più vicina.
        for idx, d in enumerate(remaining):
            leg = osrm_route(current, d["coord"])
            ev = evaluate_candidate(current_clock, leg, d)

            # Le consegne non fattibili vengono lasciate in fondo, se esistono alternative fattibili.
            score = ev["score"]

            if best_score is None or score < best_score:
                best_idx = idx
                best_score = score
                best_leg = leg
                best_eval = ev

        selected = remaining.pop(best_idx)

        warnings = []
        if best_eval.get("warning"):
            warnings.append(best_eval["warning"])

        if selected.get("sponda") and vehicle and not vehicle.get("ha_sponda"):
            warnings.append("Serve sponda ma il mezzo selezionato non la possiede")

        if selected.get("ztl") and vehicle and not vehicle.get("accesso_ztl"):
            warnings.append("Cliente in ZTL: verificare accesso mezzo")

        service_start = best_eval["service_start"]
        service_end = service_start + float(selected.get("tempo_scarico_min") or 0)

        selected["ordine"] = len(ordered) + 1
        selected["km_tappa"] = round(best_leg["km"], 2)
        selected["minuti_tappa"] = round(best_leg["min"], 1)
        selected["attesa_min"] = round(best_eval["wait"], 1)
        selected["arrivo_stimato"] = fmt_hhmm(service_start)
        selected["partenza_stimata"] = fmt_hhmm(service_end)
        selected["warning"] = "; ".join(warnings) if warnings else ""

        total_km += best_leg["km"]
        current_clock = service_end
        current = selected["coord"]
        ordered.append(selected)

    if return_depot and ordered:
        back = osrm_route(current, depot_coord)
        total_km += back["km"]
        current_clock += back["min"]

    total_min = current_clock - start_clock

    return {
        "ordered": ordered,
        "total_km": round(total_km, 2),
        "total_min": round(total_min, 1),
        "return_time": fmt_hhmm(current_clock),
        "google_maps_url": build_google_maps_url(depot_address, ordered, return_depot),
    }
