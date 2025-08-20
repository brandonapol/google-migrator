import os
import asyncio
import zipfile
import tempfile
import io
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import secrets
import json
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# Load environment variables
load_dotenv()

app = FastAPI(title="Google Drive Backup Service")
templates = Jinja2Templates(directory="templates")

class UserSession:
    def __init__(self):
        self.token: Optional[Credentials] = None
        self.state: str = ""
        self.job_id: str = ""
        self.created_at: datetime = datetime.now()
        self.progress: Dict = {
            "total_files": 0,
            "processed_files": 0,
            "current_file": "",
            "status": "idle",
            "zip_files": [],
            "error": ""
        }

class DriveBackupApp:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("REDIRECT_URL", "http://localhost:8000/auth/callback")
        
        if not self.client_id or not self.client_secret:
            print("WARNING: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env file")
        
        self.sessions: Dict[str, UserSession] = {}
        self.cleanup_interval = 3600  # 1 hour
        
        # Create downloads directory
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("templates", exist_ok=True)

    def create_flow(self):
        return Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
            redirect_uri=self.redirect_uri
        )

drive_app = DriveBackupApp()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/auth/login")
async def start_login(response: Response):
    if not drive_app.client_id or not drive_app.client_secret:
        raise HTTPException(500, "OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")
    
    session_id = secrets.token_urlsafe(32)
    state = secrets.token_urlsafe(32)
    
    session = UserSession()
    session.state = state
    drive_app.sessions[session_id] = session
    
    try:
        flow = drive_app.create_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent screen to ensure refresh token
        )
        
        response.set_cookie("session_id", session_id, max_age=3600, httponly=True, samesite="lax")
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(500, f"Failed to create OAuth flow: {str(e)}")

@app.get("/auth/callback")
async def auth_callback(request: Request):
    # Get query parameters
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    
    # Handle OAuth errors
    if error:
        error_description = request.query_params.get("error_description", "Unknown error")
        print(f"OAuth error: {error} - {error_description}")
        return RedirectResponse(f"/?error={error}")
    
    if not code or not state:
        print("Missing code or state parameter")
        return RedirectResponse("/?error=missing_parameters")
    
    # Get session
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in drive_app.sessions:
        print(f"Invalid session: {session_id}")
        return RedirectResponse("/?error=invalid_session")
    
    session = drive_app.sessions[session_id]
    
    # Validate state parameter
    if state != session.state:
        print(f"State mismatch: expected {session.state}, got {state}")
        return RedirectResponse("/?error=state_mismatch")
    
    try:
        # Create new flow and exchange code for token
        flow = drive_app.create_flow()
        flow.fetch_token(code=code)
        
        # Store credentials
        session.token = flow.credentials
        session.progress["status"] = "authenticated"
        
        print("OAuth authentication successful")
        return RedirectResponse("/dashboard", status_code=302)
        
    except Exception as e:
        print(f"Token exchange failed: {str(e)}")
        return RedirectResponse(f"/?error=token_exchange_failed")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in drive_app.sessions:
        return RedirectResponse("/")
    
    session = drive_app.sessions[session_id]
    if not session.token:
        return RedirectResponse("/")
    
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/download/start")
async def start_download(request: Request, background_tasks: BackgroundTasks):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in drive_app.sessions:
        raise HTTPException(401, "Not authenticated")
    
    session = drive_app.sessions[session_id]
    if not session.token:
        raise HTTPException(401, "Not authenticated")
    
    job_id = secrets.token_urlsafe(16)
    session.job_id = job_id
    session.progress = {
        "total_files": 0,
        "processed_files": 0,
        "current_file": "",
        "status": "starting",
        "zip_files": [],
        "error": ""
    }
    
    background_tasks.add_task(process_download, session)
    return {"job_id": job_id}

@app.get("/download/progress")
async def get_progress(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in drive_app.sessions:
        raise HTTPException(404, "Session not found")
    
    session = drive_app.sessions[session_id]
    return session.progress

@app.get("/download/{filename}")
async def download_file(request: Request, filename: str):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in drive_app.sessions:
        raise HTTPException(401, "Unauthorized")
    
    session = drive_app.sessions[session_id]
    file_path = os.path.join("downloads", session.job_id, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")
    
    return FileResponse(
        file_path, 
        filename=filename,
        media_type='application/zip'
    )

async def process_download(session: UserSession):
    try:
        session.progress["status"] = "initializing"
        print(f"Starting download process for session")
        
        # Refresh token if needed
        if session.token.expired:
            print("Refreshing expired token")
            session.token.refresh(GoogleRequest())
        
        service = build('drive', 'v3', credentials=session.token)
        
        session.progress["status"] = "listing_files"
        print("Listing files from Google Drive")
        files = await list_all_files(service)
        
        # Filter out folders and unusable files
        downloadable_files = [f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder']
        print(f"Found {len(downloadable_files)} downloadable files")
        
        session.progress["total_files"] = len(downloadable_files)
        session.progress["status"] = "downloading"
        
        await download_to_zips(service, downloadable_files, session)
        session.progress["status"] = "completed"
        print("Download process completed successfully")
        
    except Exception as e:
        session.progress["status"] = "error"
        session.progress["error"] = str(e)
        print(f"Download error: {e}")

async def list_all_files(service) -> List[Dict]:
    files = []
    page_token = None
    
    while True:
        try:
            print(f"Fetching files page (token: {page_token})")
            results = service.files().list(
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, parents, size, capabilities)",
                pageToken=page_token,
                q="trashed=false"  # Only get non-trashed files
            ).execute()
            
            items = results.get('files', [])
            files.extend(items)
            print(f"Fetched {len(items)} files, total: {len(files)}")
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        except HttpError as e:
            raise Exception(f"Failed to list files: {e}")
    
    return files

async def download_to_zips(service, files: List[Dict], session: UserSession):
    max_zip_size = 2 * 1024 * 1024 * 1024  # 2GB
    zip_index = 1
    current_zip_size = 0
    
    job_dir = os.path.join("downloads", session.job_id)
    os.makedirs(job_dir, exist_ok=True)
    print(f"Created download directory: {job_dir}")
    
    zip_file = None
    zip_writer = None
    
    try:
        for i, file in enumerate(files):
            # Check if file can be downloaded
            capabilities = file.get('capabilities', {})
            if not capabilities.get('canDownload', True):
                print(f"Skipping non-downloadable file: {file['name']}")
                session.progress["processed_files"] = i + 1
                continue
            
            file_size = int(file.get('size', 0)) or 1024
            
            # Start new zip if needed
            if zip_writer is None or current_zip_size + file_size > max_zip_size:
                if zip_writer:
                    zip_writer.close()
                    print(f"Closed zip file, size: {current_zip_size} bytes")
                
                zip_filename = f"drive_backup_{zip_index:03d}.zip"
                zip_path = os.path.join(job_dir, zip_filename)
                zip_writer = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
                current_zip_size = 0
                zip_index += 1
                
                session.progress["zip_files"].append(zip_filename)
                print(f"Created new zip file: {zip_filename}")
            
            session.progress["current_file"] = file['name']
            session.progress["processed_files"] = i + 1
            
            try:
                print(f"Downloading file {i+1}/{len(files)}: {file['name']}")
                file_content = await download_single_file(service, file)
                if file_content:
                    filename = get_safe_filename(file)
                    zip_writer.writestr(filename, file_content)
                    current_zip_size += len(file_content)
                    print(f"Added to zip: {filename} ({len(file_content)} bytes)")
                else:
                    print(f"Skipped file (no content): {file['name']}")
                    
            except Exception as e:
                print(f"Error downloading {file['name']}: {e}")
                continue
    
    finally:
        if zip_writer:
            zip_writer.close()
            print(f"Final zip file closed, size: {current_zip_size} bytes")

async def download_single_file(service, file: Dict) -> Optional[bytes]:
    try:
        file_id = file['id']
        mime_type = file['mimeType']
        
        if is_google_apps_file(mime_type):
            export_format = get_export_format(mime_type)
            request = service.files().export_media(fileId=file_id, mimeType=export_format)
        else:
            request = service.files().get_media(fileId=file_id)
        
        # Download file content
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        return file_io.getvalue()
        
    except HttpError as e:
        if e.resp.status in [403, 404]:
            # File not accessible or not found
            return None
        raise

def get_safe_filename(file: Dict) -> str:
    """Generate safe filename for zip archive"""
    name = file['name']
    mime_type = file['mimeType']
    
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    # Add extension for Google Apps files
    if is_google_apps_file(mime_type):
        extension = get_file_extension(get_export_format(mime_type))
        if not name.lower().endswith(f'.{extension}'):
            name = f"{name}.{extension}"
    
    return name

def is_google_apps_file(mime_type: str) -> bool:
    google_apps_types = {
        'application/vnd.google-apps.document',
        'application/vnd.google-apps.spreadsheet', 
        'application/vnd.google-apps.presentation',
        'application/vnd.google-apps.drawing'
    }
    return mime_type in google_apps_types

def get_export_format(mime_type: str) -> str:
    formats = {
        'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.google-apps.drawing': 'application/pdf'
    }
    return formats.get(mime_type, 'application/pdf')

def get_file_extension(mime_type: str) -> str:
    extensions = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx', 
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/pdf': 'pdf'
    }
    return extensions.get(mime_type, 'pdf')

# Cleanup old sessions periodically
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_sessions())

async def cleanup_sessions():
    while True:
        await asyncio.sleep(drive_app.cleanup_interval)
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in drive_app.sessions.items():
            # Remove sessions older than 4 hours
            if current_time - session.created_at > timedelta(hours=4):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            if session_id in drive_app.sessions:
                job_dir = os.path.join("downloads", drive_app.sessions[session_id].job_id)
                if os.path.exists(job_dir):
                    import shutil
                    shutil.rmtree(job_dir)
                del drive_app.sessions[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
