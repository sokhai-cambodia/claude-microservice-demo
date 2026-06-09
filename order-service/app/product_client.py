import os
import httpx

PRODUCT_SERVICE_URL = os.environ["PRODUCT_SERVICE_URL"]


async def get_product(product_id: int) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{PRODUCT_SERVICE_URL}/products/{product_id}",
                timeout=5.0,
            )
    except httpx.RequestError:
        return None
    if resp.status_code == 200:
        return resp.json()
    return None
