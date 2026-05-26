from fastapi import FastAPI, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime

from models.tarea import TareaEntrada, TareaActualizacion, TareaSalida

app = FastAPI(title="API de Tareas", version="1.0.0")

# Almacenamiento en memoria
tareas: dict[int, dict] = {}
contador_id = 0


def _siguiente_id() -> int:
    global contador_id
    contador_id += 1
    return contador_id


def _tarea_a_salida(t: dict) -> TareaSalida:
    return TareaSalida(**t)


ORDEN_PRIORIDAD = {"baja": 0, "media": 1, "alta": 2}


# GET /tareas/estadisticas  — debe ir ANTES de /tareas/{id}
@app.get("/tareas/estadisticas")
def estadisticas():
    total = len(tareas)
    completadas = sum(1 for t in tareas.values() if t["completada"])
    pendientes = total - completadas

    pendientes_por_prioridad = {"baja": 0, "media": 0, "alta": 0}
    for t in tareas.values():
        if not t["completada"]:
            pendientes_por_prioridad[t["prioridad"]] += 1

    return {
        "total": total,
        "completadas": completadas,
        "pendientes": pendientes,
        "pendientes_por_prioridad": pendientes_por_prioridad,
    }


# GET /tareas
@app.get("/tareas", response_model=list[TareaSalida])
def listar_tareas(
    completada: Optional[bool] = Query(None),
    prioridad: Optional[Literal["baja", "media", "alta"]] = Query(None),
    ordenar: Optional[Literal["prioridad", "creada_en", "fecha_limite"]] = Query(None),
    dir: Optional[Literal["asc", "desc"]] = Query("asc"),
    limite: Optional[int] = Query(None, ge=1),
    pagina: Optional[int] = Query(1, ge=1),
):
    resultado = list(tareas.values())

    if completada is not None:
        resultado = [t for t in resultado if t["completada"] == completada]

    if prioridad is not None:
        resultado = [t for t in resultado if t["prioridad"] == prioridad]

    if ordenar == "prioridad":
        resultado.sort(key=lambda t: ORDEN_PRIORIDAD[t["prioridad"]], reverse=(dir == "desc"))
    elif ordenar == "creada_en":
        resultado.sort(key=lambda t: t["creada_en"], reverse=(dir == "desc"))
    elif ordenar == "fecha_limite":
        resultado.sort(
            key=lambda t: (t["fecha_limite"] is None, t["fecha_limite"]),
            reverse=(dir == "desc"),
        )

    if limite is not None:
        inicio = (pagina - 1) * limite
        resultado = resultado[inicio: inicio + limite]

    return [_tarea_a_salida(t) for t in resultado]


# GET /tareas/{id}
@app.get("/tareas/{tarea_id}", response_model=TareaSalida)
def obtener_tarea(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return _tarea_a_salida(tareas[tarea_id])


# POST /tareas
@app.post("/tareas", response_model=TareaSalida, status_code=201)
def crear_tarea(entrada: TareaEntrada):
    tarea_id = _siguiente_id()
    tarea = {
        "id": tarea_id,
        "titulo": entrada.titulo,
        "descripcion": entrada.descripcion,
        "prioridad": entrada.prioridad,
        "completada": False,
        "creada_en": datetime.utcnow(),
        "completada_en": None,
        "fecha_limite": entrada.fecha_limite,
    }
    tareas[tarea_id] = tarea
    return _tarea_a_salida(tarea)


# POST /tareas/lote  (bonus) — antes de /tareas/{id}/completar para evitar conflictos
@app.post("/tareas/lote", response_model=list[TareaSalida], status_code=201)
def crear_lote(entradas: list[TareaEntrada]):
    creadas = []
    for entrada in entradas:
        tarea_id = _siguiente_id()
        tarea = {
            "id": tarea_id,
            "titulo": entrada.titulo,
            "descripcion": entrada.descripcion,
            "prioridad": entrada.prioridad,
            "completada": False,
            "creada_en": datetime.utcnow(),
            "completada_en": None,
            "fecha_limite": entrada.fecha_limite,
        }
        tareas[tarea_id] = tarea
        creadas.append(tarea)
    return [_tarea_a_salida(t) for t in creadas]


# PATCH /tareas/{id}
@app.patch("/tareas/{tarea_id}", response_model=TareaSalida)
def actualizar_tarea(tarea_id: int, actualizacion: TareaActualizacion):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    tarea = tareas[tarea_id]
    datos = actualizacion.model_dump(exclude_unset=True)

    if "completada" in datos and datos["completada"] and not tarea["completada"]:
        datos["completada_en"] = datetime.utcnow()
    elif "completada" in datos and not datos["completada"]:
        datos["completada_en"] = None

    tarea.update(datos)
    return _tarea_a_salida(tarea)


# DELETE /tareas/{id}
@app.delete("/tareas/{tarea_id}", status_code=204)
def eliminar_tarea(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    del tareas[tarea_id]


# POST /tareas/{id}/completar
@app.post("/tareas/{tarea_id}/completar", response_model=TareaSalida)
def completar_tarea(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    tarea = tareas[tarea_id]
    if tarea["completada"]:
        raise HTTPException(status_code=400, detail="La tarea ya está completada")

    tarea["completada"] = True
    tarea["completada_en"] = datetime.utcnow()
    return _tarea_a_salida(tarea)
