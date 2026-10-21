import asyncio, re, sqlite3, time, unicodedata
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent

BASE = Path(__file__).parent
DB = BASE / "votes.db"

app = FastAPI(title="TikTok Live Vote")
app.mount("/static", StaticFiles(directory=str(BASE/"static")), name="static")

scores = {"messi": 0, "ronaldo": 0}
viewers = 0
connected = False
connecting = False
username = ""
client = None
clients = set()
stop_requested = False
last_error = ""
started_at = None

# Exact whole-comment matching. Add aliases here if you want more spellings.
ALIASES = {
    "messi": "messi",
    "ronaldo": "ronaldo",
    "ronsldo": "ronaldo",
}

def db():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("""CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team TEXT NOT NULL,
        comment TEXT NOT NULL,
        username TEXT,
        created_at REAL NOT NULL
    )""")
    return con

def load_scores():
    global scores
    con=db()
    rows=con.execute("SELECT team, COUNT(*) FROM votes GROUP BY team").fetchall()
    scores={"messi":0,"ronaldo":0}
    for team,n in rows:
        scores[team]=n
    con.close()

def normalize(s):
    s=unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", " ", s.strip().casefold())

def classify(comment):
    return ALIASES.get(normalize(comment))

def save_vote(team, comment, user):
    con=db()
    con.execute("INSERT INTO votes(team,comment,username,created_at) VALUES(?,?,?,?)",
                (team,comment,user,time.time()))
    con.commit(); con.close()

def count_votes():
    con=db()
    n=con.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    con.close()
    return n

async def broadcast():
    msg={"type":"state","scores":scores,"connected":connected,"username":username,
         "viewers":viewers,"total_votes":count_votes(),"error":last_error}
    dead=[]
    for ws in list(clients):
        try: await ws.send_json(msg)
        except: dead.append(ws)
    for ws in dead: clients.discard(ws)

async def add_vote(comment, user):
    team=classify(comment)
    if not team: return
    scores[team]+=1
    save_vote(team, comment, user)
    await broadcast()

async def connect_once(target):
    global client, connected, connecting, last_error, started_at
    connecting=True
    connected=False
    last_error=""
    await broadcast()
    try:
        client=TikTokLiveClient(unique_id=target)
        @client.on(ConnectEvent)
        async def on_connect(event):
            global connected, connecting, started_at, last_error
            connected=True; connecting=False; started_at=time.time(); last_error=""
            await broadcast()

        @client.on(DisconnectEvent)
        async def on_disconnect(event):
            global connected
            connected=False
            await broadcast()

        @client.on(CommentEvent)
        async def on_comment(event):
            user=getattr(getattr(event,"user",None),"unique_id","")
            await add_vote(event.comment, user)

        await client.start()
    except Exception as e:
        connected=False; connecting=False
        last_error=str(e)[:240]
        await broadcast()

async def monitor(target):
    global stop_requested
    stop_requested=False
    while not stop_requested:
        if not connected and not connecting:
            await connect_once(target)
        await asyncio.sleep(8)

class ConnectBody(BaseModel):
    username: str

@app.on_event("startup")
async def startup():
    load_scores()

@app.get("/")
async def root():
    return FileResponse(BASE/"static/index.html")

@app.get("/overlay")
async def overlay():
    return FileResponse(BASE/"static/overlay.html")

@app.post("/api/connect")
async def connect(body: ConnectBody):
    global username, stop_requested
    target=body.username.strip().lstrip("@")
    if not target: return {"ok":False,"error":"TikTok username is required"}
    username=target
    stop_requested=True
    await asyncio.sleep(0.1)
    asyncio.create_task(monitor(target))
    return {"ok":True,"username":target}

@app.post("/api/reset")
async def reset():
    global scores
    con=db(); con.execute("DELETE FROM votes"); con.commit(); con.close()
    scores={"messi":0,"ronaldo":0}
    await broadcast()
    return {"ok":True}

@app.get("/api/status")
async def status():
    return {"connected":connected,"connecting":connecting,"username":username,
            "scores":scores,"total_votes":count_votes(),"error":last_error}

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept(); clients.add(websocket)
    await websocket.send_json({"type":"state","scores":scores,"connected":connected,
        "username":username,"viewers":viewers,"total_votes":count_votes(),"error":last_error})
    try:
        while True: await websocket.receive_text()
    except: clients.discard(websocket)
