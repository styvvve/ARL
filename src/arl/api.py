from fastapi import FastAPI

app = FastAPI() #nom de l'API

@app.get("/")
def tache_racine():
    return {"status": "ok"}

@app.get("/taches/{tache_id}")
def getTache(tache_id: int):
    return {"status": "ok"}
