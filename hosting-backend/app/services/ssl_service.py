def issue_ssl(domain: str):
    cmd = f"certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain}"
    os.system(cmd)