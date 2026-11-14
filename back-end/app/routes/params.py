"""Parâmetros de consulta compartilhados (documentação do OpenAPI)."""
from fastapi import Query

BBOX = Query(..., description='oeste,sul,leste,norte em graus; oeste > leste cruza o antimeridiano',
             examples=['-58,-22,-54,-16'])
