def create_vhost(domain: str, site_name: str):
    config = f"""
server {{
    server_name {domain};
    root /var/www/{site_name};

    index index.html index.php;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""
    path = f"/etc/nginx/sites-available/{site_name}.conf"
    with open(path, "w") as f:
        f.write(config)

    os.system(f"ln -s {path} /etc/nginx/sites-enabled/")
    os.system("systemctl reload nginx")