class SiteService:

    def create_site(domain, site_name):
        path = f"/var/www/{site_name}"

        os.makedirs(path, exist_ok=True)

        NginxService.create_vhost(domain, site_name)
        SSLService.issue_ssl(domain)

        return {"status": "created"}