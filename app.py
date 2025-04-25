from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import math
from operator import itemgetter

app = FastAPI()
templates = Jinja2Templates(directory="templates")

coord = {
    'EDO.MEX': (19.2917297, -99.6631835),
    'QRO': (20.5933266, -100.3926262),
    'CDMX': (19.4326419, -99.1381924),
    'SLP': (22.1140562, -100.9983314),
    'MTY': (25.6808582, -100.3124481),
    'PUE': (19.036459, -98.2096953),
    'GDL': (20.6772448, -103.3466192),
    'MICH': (19.7036142, -101.1915685),
    'SON': (30.2275108, -110.4130477)
}

pedidos = {
    "EDO.MEX": {"cantidad": 10, "categoria": "alimentos", "prioridad": 2},
    "QRO": {"cantidad": 13, "categoria": "quimicos", "prioridad": 1},
    "CDMX": {"cantidad": 7, "categoria": "alimentos", "prioridad": 1},
    "SLP": {"cantidad": 11, "categoria": "ropa", "prioridad": 2},
    "MTY": {"cantidad": 15, "categoria": "ropa", "prioridad": 1},
    "PUE": {"cantidad": 8, "categoria": "alimentos", "prioridad": 2},
    "GDL": {"cantidad": 6, "categoria": "quimicos", "prioridad": 3},
    "MICH": {"cantidad": 7, "categoria": "alimentos", "prioridad": 1},
    "SON": {"cantidad": 12, "categoria": "quimicos", "prioridad": 3}
}

almacen = (19.4326419, -99.1381924)
max_carga = 40
categorias_incompatibles = {("alimentos", "quimicos"), ("quimicos", "alimentos")}
velocidad_promedio = 60  # km/h

def distancia(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 111  # Aprox. km

def peso_ruta(ruta):
    return sum(pedidos[c]["cantidad"] for c in ruta)

def tiempo_transcurrido(ruta):
    dist_total = sum(distancia(coord[ruta[i]], coord[ruta[i+1]]) for i in range(len(ruta)-1))
    return round(dist_total / velocidad_promedio, 2)

def gasto_comidas(ruta):
    return sum(pedidos[c]["cantidad"] * 5 for c in ruta if pedidos[c]["categoria"] == "alimentos")

def en_ruta(rutas, c):
    return next((r for r in rutas if c in r), None)

def vrp_voraz():
    s = {}
    for c1 in coord:
        for c2 in coord:
            if c1 != c2 and (c2, c1) not in s:
                d1, d2 = distancia(coord[c1], almacen), distancia(coord[c2], almacen)
                s[(c1, c2)] = d1 + d2 - distancia(coord[c1], coord[c2])
    s = sorted(s.items(), key=itemgetter(1), reverse=True)
    
    rutas = []
    for (c1, c2), _ in s:
        rc1, rc2 = en_ruta(rutas, c1), en_ruta(rutas, c2)
        if rc1 is None and rc2 is None:
            nueva = [c1, c2]
            if peso_ruta(nueva) <= max_carga:
                rutas.append(nueva)
        elif rc1 and not rc2:
            if rc1[0] == c1 and peso_ruta(rc1) + pedidos[c2]["cantidad"] <= max_carga:
                rc1.insert(0, c2)
            elif rc1[-1] == c1 and peso_ruta(rc1) + pedidos[c2]["cantidad"] <= max_carga:
                rc1.append(c2)
        elif not rc1 and rc2:
            if rc2[0] == c2 and peso_ruta(rc2) + pedidos[c1]["cantidad"] <= max_carga:
                rc2.insert(0, c1)
            elif rc2[-1] == c2 and peso_ruta(rc2) + pedidos[c1]["cantidad"] <= max_carga:
                rc2.append(c1)
        elif rc1 and rc2 and rc1 != rc2:
            if rc1[0] == c1 and rc2[-1] == c2 and peso_ruta(rc1) + peso_ruta(rc2) <= max_carga:
                rc2.extend(rc1)
                rutas.remove(rc1)
            elif rc1[-1] == c1 and rc2[0] == c2 and peso_ruta(rc1) + peso_ruta(rc2) <= max_carga:
                rc1.extend(rc2)
                rutas.remove(rc2)
    return rutas

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    rutas = vrp_voraz()
    
    # Añadir impresión de depuración para ver las rutas
    print("Rutas generadas:", rutas)

    distancias_rutas = [round(sum(distancia(coord[r[i]], coord[r[i+1]]) for i in range(len(r)-1)), 2) for r in rutas]
    tiempos = [tiempo_transcurrido(r) for r in rutas]
    gastos = [gasto_comidas(r) for r in rutas]
    cargas = [peso_ruta(r) for r in rutas]

    rutas_completas = []
    for ruta, carga, distancia_ruta, tiempo, gasto in zip(rutas, cargas, distancias_rutas, tiempos, gastos):
        rutas_completas.append({
            "ruta": ruta,
            "carga": carga,
            "distancia": distancia_ruta,
            "tiempo": tiempo,
            "gasto": gasto
        })

    restricciones = {
        "max_carga": max_carga,
        "categorias_incompatibles": categorias_incompatibles,
        "velocidad_promedio": velocidad_promedio,
    }

    return templates.TemplateResponse("mapa.html", {
        "request": request,
        "rutas_completas": rutas_completas,
        "restricciones": restricciones,
        "coord": coord,
        "almacen": almacen  # ✅ añade la ubicación del almacén
    })
