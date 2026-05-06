from fastapi import APIRouter

router = APIRouter()

@router.post("/sites")
def create_site(payload: dict):
    return SiteService.create_site(
        payload["domain"],
        payload["site_name"]
    )