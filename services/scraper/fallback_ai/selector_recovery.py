"""Fallback de recuperación cuando un selector CSS deja de matchear.

Estrategia: si un spider devuelve 0 items dos corridas seguidas, se manda
el HTML crudo de la página a Claude para que proponga selectores nuevos.
Esto NO reemplaza el mantenimiento manual del spider — es una alarma
temprana + sugerencia, no una auto-reparación en producción sin revisión.
"""

import os

from anthropic import Anthropic

RECOVERY_PROMPT = """El siguiente HTML es de una página de listado de productos
de e-commerce. El selector CSS anterior era '{old_selector}' y ya no
encuentra elementos. Proponé un selector CSS actualizado para la tarjeta
de producto, el título, el precio y el link. Responde solo JSON:
{{"card": "...", "title": "...", "price": "...", "link": "..."}}"""


def suggest_new_selectors(html_snippet: str, old_selector: str) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": RECOVERY_PROMPT.format(old_selector=old_selector)
                + "\n\n"
                + html_snippet[:8000],
            }
        ],
    )
    return response.content[0].text
