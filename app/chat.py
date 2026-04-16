"""
chat.py — Motor de conversación multi-proveedor (Anthropic / OpenAI)
Controla el proveedor con LLM_PROVIDER en .env:
  LLM_PROVIDER=anthropic  → Claude
  LLM_PROVIDER=openai     → GPT
"""

import os
from dotenv import load_dotenv
from app.tools import bookly, rag

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai":    "gpt-4o-mini",
}
LLM_MODEL = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(LLM_PROVIDER, "gpt-4o-mini")

SYSTEM_PROMPT = """Eres el asistente virtual de Nomadas Surf Park, una escuela de surf y actividades acuáticas ubicada en El Puerto de Santa María (Cádiz).
Tu objetivo es ayudar a los usuarios a:
1. Conocer los servicios y actividades disponibles
2. Consultar horarios y disponibilidad de plazas
3. Resolver dudas sobre normas, equipamiento y política del centro
4. Orientarles hacia la reserva online en nomadassurfpark.com
5. Si un usuario saluda sin especificar qué quiere, pregúntale qué actividad le interesa y muéstrale las opciones disponibles.
6. Si solicitan información que no tienes, diles con honestidad que no puedes ayudar con eso y que lo mejor es contactar por Whatsapp al número 678 685 525 o email unai@nomadassurfpark.com
7. Siempre responde de forma amigable, cercana y entusiasta, reflejando el espíritu de una escuela de surf en la playa 🏄
8. Si te preguntan por el servicio de surfing indica que tienes opción de surfin libre o con monitor.
9. No ofrezcas información que no tengas, y si no sabes algo, dilo con honestidad e indica que lo mejor es contactar por Whatsapp al número 678 685 525 o email unai@nomadassurfpark.com 
10. No te inventes horarios ni precios, si no los tienes, di que lo mejor es contactar por Whatsapp al número 678 685 525 o email
11. No te inventes actividades que no tengas, no tenemos Skimboarding, ni acampada,si no las tienes, di que lo mejor es contactar por Whatsapp al número 678 685 525 o email

Estilo de respuesta:
- Sé amigable, cercano y entusiasta (somos una escuela de surf en la playa 🏄)
- Responde siempre en español
- Cuando muestres opciones, usa formato de lista clara
- Para reservar, indica siempre la web: nomadassurfpark.com
- Si no tienes información, dilo con honestidad

Cuando el usuario saluda sin especificar qué quiere, pregúntale qué actividad le interesa y muéstrale las opciones disponibles."""

TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "Devuelve la lista de actividades con precio, duración y aforo.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Consulta horarios con plazas libres. Devuelve fecha, hora, monitor y plazas disponibles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Nombre o parte del nombre del servicio (ej: surf, skate, supyoga)"},
                    "desde":        {"type": "string", "description": "Fecha inicio YYYY-MM-DD (opcional)"},
                    "hasta":        {"type": "string", "description": "Fecha fin YYYY-MM-DD (opcional)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schedule",
            "description": "Devuelve los horarios de apertura y días disponibles.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Busca en documentos internos: normas, cancelación, equipamiento, FAQs, declaración de riesgos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Pregunta o tema a buscar"}
                },
                "required": ["query"],
            },
        },
    },
]

TOOLS_ANTHROPIC = [
    {
        "name": "get_services",
        "description": "Devuelve la lista de actividades con precio, duración y aforo.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_available_slots",
        "description": "Consulta horarios con plazas libres. Devuelve fecha, hora, monitor y plazas disponibles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Nombre o parte del nombre del servicio"},
                "desde":        {"type": "string", "description": "Fecha inicio YYYY-MM-DD (opcional)"},
                "hasta":        {"type": "string", "description": "Fecha fin YYYY-MM-DD (opcional)"},
            },
            "required": [],
        },
    },
    {
        "name": "get_schedule",
        "description": "Devuelve horarios de apertura y días disponibles.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_knowledge",
        "description": "Busca en documentos internos: normas, cancelación, equipamiento, FAQs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Pregunta o tema a buscar"}
            },
            "required": ["query"],
        },
    },
]


async def run_tool(name: str, inputs: dict) -> str:
    from datetime import date
    try:
        if name == "get_services":
            data = await bookly.get_services()
            if not data:
                return "No se encontraron servicios."
            lines = ["**Nuestras actividades:**\n"]
            for s in data:
                lines.append(
                    f"• **{s['title']}** — {s['precio']}€ · "
                    f"{s['duracion_minutos']} min · Aforo: {s['aforo_maximo']} personas"
                )
            return "\n".join(lines)

        elif name == "get_available_slots":
            service_name = inputs.get("service_name")
            desde = date.fromisoformat(inputs["desde"]) if inputs.get("desde") else None
            hasta = date.fromisoformat(inputs["hasta"]) if inputs.get("hasta") else None
            slots = (await bookly.get_slots_by_service_name(service_name)
                     if service_name
                     else await bookly.get_available_slots(desde=desde, hasta=hasta))
            if not slots:
                return "No hay plazas disponibles para esa actividad en las fechas indicadas."
            lines = [f"**Plazas disponibles{' — ' + service_name if service_name else ''}:**\n"]
            for s in slots[:15]:
                lines.append(
                    f"• {s.get('dia_semana','')} {s.get('fecha','')} a las {s.get('hora','')} "
                    f"— {s['servicio']} "
                    f"({s['plazas_libres']} plaza{'s' if s['plazas_libres'] != 1 else ''} libre{'s' if s['plazas_libres'] != 1 else ''})"
                )
            return "\n".join(lines)

        elif name == "get_schedule":
            schedule = await bookly.get_schedule()
            if not schedule:
                return "No se pudieron obtener los horarios."
            by_staff: dict = {}
            for row in schedule:
                by_staff.setdefault(row["full_name"], []).append(row)
            lines = ["**Horarios de apertura:**\n"]
            for staff_name, days in by_staff.items():
                lines.append(f"\n*{staff_name}:*")
                for d in days:
                    if d["abierto"]:
                        lines.append(f"  {d['dia']}: {d['start_time']} – {d['end_time']}")
                    else:
                        lines.append(f"  {d['dia']}: Cerrado")
            return "\n".join(lines)

        elif name == "search_knowledge":
            results = rag.search(inputs.get("query", ""))
            if not results:
                return "No encontré información específica sobre ese tema."
            return "\n---\n".join(f"[{r['fuente']}]\n{r['texto']}" for r in results)

        return f"Herramienta '{name}' no reconocida."
    except Exception as e:
        return f"Error al consultar '{name}': {str(e)}"


async def _chat_anthropic(messages: list[dict]) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    current = list(messages)
    while True:
        response = await client.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS_ANTHROPIC,
            messages=current,
        )
        if response.stop_reason == "tool_use":
            current.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await run_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            current.append({"role": "user", "content": tool_results})
            continue
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
    return "No pude generar una respuesta."


async def _chat_openai(messages: list[dict]) -> str:
    import json
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    current = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)
    while True:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            tools=TOOLS_OPENAI,
            messages=current,
            max_tokens=1024,
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            current.append(msg)
            for tc in msg.tool_calls:
                inputs = json.loads(tc.function.arguments)
                result = await run_tool(tc.function.name, inputs)
                current.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue
        return msg.content or "No pude generar una respuesta."


async def chat(messages: list[dict]) -> str:
    if LLM_PROVIDER == "anthropic":
        return await _chat_anthropic(messages)
    elif LLM_PROVIDER == "openai":
        return await _chat_openai(messages)
    else:
        raise ValueError(f"LLM_PROVIDER '{LLM_PROVIDER}' no válido. Usa: anthropic u openai")
