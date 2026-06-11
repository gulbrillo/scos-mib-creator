from fastapi import APIRouter, Depends

from ..security import get_current_user
from mibschema.registry import registry_as_json
from mibschema.pus import ptcpfc_catalog_json, pus_services_json

router = APIRouter(prefix="/api", tags=["schema"], dependencies=[Depends(get_current_user)])


@router.get("/schema")
def get_schema():
    return registry_as_json()


@router.get("/pus/types")
def get_pus_types():
    return ptcpfc_catalog_json()


@router.get("/pus/services")
def get_pus_services():
    return pus_services_json()
