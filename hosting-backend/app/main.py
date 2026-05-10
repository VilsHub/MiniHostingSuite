
from fastapi import FastAPI, HTTPException, UploadFile, File,  Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils import shell
import time
import os
from fastapi import HTTPException
from fastapi.responses import FileResponse
import subprocess
import shutil
import zipfile
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# ========================
# CONFIG
# ========================
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "hosting")
DB_PASSWORD = os.getenv("DB_PASSWORD", "hostingpass")
DB_NAME = os.getenv("DB_NAME", "hosting")
MAX_SIZE = 100 * 1024 * 1024  # 100MB

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
BASE_PATH = "/var/www"
PHP_VERSIONS = {
    "7.4": "php74:9000",
    "8.0": "php80:9000",
    "8.1": "php81:9000",
    "8.2": "php82:9000"
}
# ========================
# DB SETUP
# ========================
for i in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        Base = declarative_base()
        engine.connect()
        break
    except Exception:
        time.sleep(3)

class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    domain = Column(String(255))
    php_version = Column(String(5))
    path = Column(String(255))
    db_name = Column(String(100))
    status = Column(String(50))
class FolderCreate(BaseModel):
    path: str
    name: str
class SFTPRequest(BaseModel):
    password: str
Base.metadata.create_all(bind=engine)

# ========================
# APP INIT
# ========================
app = FastAPI()

# Enable CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# REQUEST MODELS
# ========================
class SiteCreate(BaseModel):
    domain: str
    site_name: str
    php_version: str = "8.2"

# ========================
# UTILS
# ========================
def run(cmd: str):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return result.stdout
# ========================
# CORE LOGIC
# ========================
def create_nginx_config(domain: str, site_name: str, php_version: str = "8.2"):
    os.makedirs("/etc/nginx/conf.d", exist_ok=True)

    path = f"/etc/nginx/conf.d/{site_name}.conf"

    php_socket = PHP_VERSIONS.get(php_version, "php82:9000")

    config = f"""
server {{
    listen 80;
    server_name {domain};
    limit_req zone=general burst=20 nodelay;

    root /var/www/{site_name}/html;
    index index.php index.html;

    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \.php$ {{
        include fastcgi_params;
        fastcgi_pass {php_socket};
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        fastcgi_read_timeout 300;
    }}

    location ~ /\.ht {{
        deny all;
    }}
}}
"""

    with open(path, "w") as f:
        f.write(config)

    run("docker exec hosting_nginx nginx -s reload")

def create_ssl_config(domain, site_name, php_version="8.2"):
    php_socket = PHP_VERSIONS.get(php_version, "php82:9000")

    return f"""
server {{
    listen 80;
    server_name {domain};
    limit_req zone=general burst=20 nodelay;
    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}

    location / {{
        return 301 https://$host$request_uri;
    }}
}}

server {{
    listen 443 ssl;
    server_name {domain} www.{domain};
    limit_req zone=general burst=20 nodelay;
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    root /var/www/{site_name}/html;
    index index.php index.html;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \.php$ {{
        include fastcgi_params;
        fastcgi_pass {php_socket};
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        fastcgi_read_timeout 300;
    }}

    location ~ /\.ht {{
        deny all;
    }}
}}
"""

def issue_ssl(domain: str):

    cmd = [
        "docker", "run", "--rm",
        "-v", "/etc/letsencrypt:/etc/letsencrypt",
        "-v", "/var/www/certbot:/var/www/certbot",
        "-v", "/var/log/letsencrypt:/var/log/letsencrypt",
        "certbot/certbot",
        "certonly",
        "--webroot",
        "-w", "/var/www/certbot",
        "-d", domain,
        "-d", f"www.{domain}",
        "--email", f"admin@{domain}",
        "--agree-tos",
        "--no-eff-email",
        "--non-interactive"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(result.stderr)

    return result.stdout

def safe_path(site_name: str, subpath: str = ""):
    base = os.path.join(BASE_PATH, site_name)
    full_path = os.path.abspath(os.path.join(base, subpath))

    if not full_path.startswith(base):
        raise HTTPException(status_code=400, detail="Invalid path")

    return full_path

def add_sftp_user(site_name: str, password: str):

    line = f"{site_name}:{password}:::html\n"

    with open("/etc/sftp/users.conf", "a") as f:
        f.write(line)

    # reload container
    subprocess.run("docker restart hosting_sftp", shell=True)

def setup_site_filesystem(site_name: str):
    base_path = f"/var/www/{site_name}"
    files_path = f"{base_path}/html"

    # Create directories
    os.makedirs(files_path, exist_ok=True)

    # 🔐 Required for SFTP chroot
    subprocess.run(f"chown root:root {base_path}", shell=True)
    subprocess.run(f"chmod 755 {base_path}", shell=True)

    # Writable folder for user
    subprocess.run(f"chown 1000:1000 {files_path}", shell=True)
    subprocess.run(f"chmod 755 {files_path}", shell=True)
# ========================
# ROUTES
# ========================

@app.get("/")
def root():
    return {"message": "Hosting Panel API running"}

@app.get("/sites")
def list_sites():
    db = SessionLocal()
    sites = db.query(Site).all()
    return [
        {
            "name": s.name,
            "domain": s.domain,
            "path": s.path,
            "status": s.status,
            "php_version": s.php_version
        }
        for s in sites
    ]

@app.post("/sites")
def create_site(payload: SiteCreate):
    db = SessionLocal()

    site_path = f"/var/www/{payload.site_name}/html"

    # 1. Create directory
    os.makedirs(site_path, exist_ok=True)
    setup_site_filesystem(payload.site_name)

    # Add default index.php
    with open(os.path.join(site_path, "index.php"), "w") as f:
        f.write("<?php phpinfo(); ?>")

    # 2. Create nginx config, ✅ pass php version
    create_nginx_config(payload.domain, payload.site_name, payload.php_version)

    site = Site(
        name=payload.site_name,
        domain=payload.domain,
        php_version=payload.php_version,  # ✅ SAVE IT
        path=site_path,
        db_name=f"{payload.site_name}_db",
        status="active"
    )

    db.add(site)
    db.commit()

    return {"message": "Site created"}

@app.delete("/sites/{site_name}")
def delete_site(site_name: str):

    db = SessionLocal()

    site = db.query(Site).filter(Site.name == site_name).first()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # =========================
    # 1. Remove site files
    # =========================
    site_root = f"/var/www/{site_name}"

    if os.path.exists(site_root):
        shutil.rmtree(site_root)

    # =========================
    # 2. Remove nginx config
    # =========================
    nginx_conf = f"/etc/nginx/conf.d/{site_name}.conf"

    if os.path.exists(nginx_conf):
        os.remove(nginx_conf)

    # =========================
    # 3. Remove Let's Encrypt SSL
    # =========================
    ssl_paths = [
        f"/etc/letsencrypt/live/{site.domain}",
        f"/etc/letsencrypt/archive/{site.domain}",
        f"/etc/letsencrypt/renewal/{site.domain}.conf"
    ]

    for path in ssl_paths:
        if os.path.exists(path):

            if os.path.isdir(path):
                shutil.rmtree(path)

            else:
                os.remove(path)

    # =========================
    # 4. Remove SFTP user
    # =========================
    users_conf = "/etc/sftp/users.conf"

    if os.path.exists(users_conf):

        with open(users_conf, "r") as f:
            lines = f.readlines()

        with open(users_conf, "w") as f:
            for line in lines:
                if not line.startswith(f"{site_name}:"):
                    f.write(line)

        subprocess.run(
            "docker restart hosting_sftp",
            shell=True
        )

    # =========================
    # 5. Optional DB deletion
    # =========================
    # Uncomment if needed

    # run(
    #     f'mysql -u root -pYOURPASS -e "DROP DATABASE {site.db_name};"'
    # )

    # =========================
    # 6. Reload nginx
    # =========================
    run("docker exec hosting_nginx nginx -s reload")

    # =========================
    # 7. Delete DB record
    # =========================
    db.delete(site)
    db.commit()

    return {
        "message": f"{site_name} deleted successfully"
    }

@app.post("/sites/{site_name}/ssl")
def generate_ssl(site_name: str):
    db = SessionLocal()
    site = db.query(Site).filter(Site.name == site_name).first()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # ✅ 1. Ensure HTTP config WITH PHP (important for ACME + consistency)
    create_nginx_config(site.domain, site.name, site.php_version)

    # ✅ 2. Issue SSL
    try:
        issue_ssl(site.domain)

        # ✅ 3. Generate SSL config WITH PHP
        config = create_ssl_config(site.domain, site.name, site.php_version)

        path = f"/etc/nginx/conf.d/{site.name}.conf"

        with open(path, "w") as f:
            f.write(config)

        # ✅ 4. Reload nginx
        run("docker exec hosting_nginx nginx -s reload")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSL failed: {str(e)}")

    return {"message": "SSL enabled"}

@app.put("/sites/{site_name}/php")
def change_php(site_name: str, version: str):
    db = SessionLocal()
    site = db.query(Site).filter(Site.name == site_name).first()

    if not site:
        raise HTTPException(404, "Site not found")

    if version not in PHP_VERSIONS:
        raise HTTPException(400, "Invalid PHP version")

    site.php_version = version
    db.commit()

    # regenerate config
    config = create_ssl_config(site.domain, site.name, version) \
        if os.path.exists(f"/etc/letsencrypt/live/{site.domain}") \
        else create_nginx_config(site.domain, site.name, version)

    path = f"/etc/nginx/conf.d/{site.name}.conf"

    with open(path, "w") as f:
        f.write(config if isinstance(config, str) else "")

    run("docker exec hosting_nginx nginx -s reload")

    return {"message": f"PHP version changed to {version}"}

@app.post("/sites/{site_name}/upload")
async def upload_file(site_name: str, file: UploadFile = File(...)):
    site_path = os.path.join(BASE_PATH, site_name, "html")

    if not os.path.exists(site_path):
        raise HTTPException(status_code=404, detail="Site not found")

    file_path = os.path.join(site_path, file.filename)

    if ".." in file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    shutil.rmtree(site_path)
    os.makedirs(site_path, exist_ok=True)

    # Save file (streaming, not memory-heavy)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # If ZIP → extract
    if file.filename.endswith(".zip"):
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(site_path)
            os.remove(file_path)  # remove zip after extraction
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

    return {"message": "Upload successful"}

@app.get("/sites/{site_name}/files")
def list_files(site_name: str, path: str = ""):
    dir_path = safe_path(site_name, path)

    if not os.path.exists(dir_path):
        raise HTTPException(404, "Path not found")

    items = []

    for name in os.listdir(dir_path):
        full = os.path.join(dir_path, name)
        items.append({
            "name": name,
            "is_dir": os.path.isdir(full),
            "size": os.path.getsize(full)
        })

    return items

@app.post("/sites/{site_name}/upload")
async def upload_file(site_name: str, path: str = "", file: UploadFile = File(...)):
    dir_path = safe_path(site_name, path)

    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if file.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(dir_path)
        os.remove(file_path)

    return {"message": "Uploaded"}

@app.get("/sites/{site_name}/download")
def download_file(site_name: str, path: str):
    file_path = safe_path(site_name, path)

    if not os.path.isfile(file_path):
        raise HTTPException(404, "File not found")

    return FileResponse(file_path, filename=os.path.basename(file_path))

@app.delete("/sites/{site_name}/delete")
def delete_file(site_name: str, path: str):
    file_path = safe_path(site_name, path)

    if os.path.isdir(file_path):
        shutil.rmtree(file_path)
    else:
        os.remove(file_path)

    return {"message": "Deleted"}

@app.post("/sites/{site_name}/mkdir")
def create_folder(site_name: str, payload: FolderCreate):
    dir_path = safe_path(site_name, payload.path)
    new_path = os.path.join(dir_path, payload.name)

    os.makedirs(new_path, exist_ok=True)

    return {"message": "Folder created"}

@app.post("/sites/{site_name}/sftp")
def enable_sftp(site_name: str, payload: SFTPRequest):
    add_sftp_user(site_name, payload.password)
    return {"message": "SFTP enabled"}