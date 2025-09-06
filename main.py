from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ocr_pipeline import process_upload, PipelineConfig

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CFG = PipelineConfig()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
async def ingest(file: UploadFile):
    try:
        blob = await file.read()
        exp = process_upload(blob, file.filename, file.content_type, CFG)
        return {"draft": exp.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")
