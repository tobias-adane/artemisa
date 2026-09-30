"""Carga el día de demo de docs/02-PRODUCTO.md para user_lab, relativo al día de hoy.

Uso (desde server/, con DATABASE_URL y LAB_BRIDGE_TOKEN en el entorno):

    uv run python -m artemisa.lab.seed_demo [--attention]
"""

import argparse
import asyncio
import hashlib
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import asyncpg

USER_ID = "user_lab"
SPACES = ("Kitchen", "Driveway", "Living Room", "Front Door")
THREAD_LENGTH = timedelta(minutes=5)


@dataclass(frozen=True)
class DemoLayer:
    captured_at: datetime
    description: str


@dataclass(frozen=True)
class DemoThread:
    space: str
    start_time: datetime
    end_time: datetime
    narrative: str
    reasoning: str
    classification: str = "normal"
    unfamiliar_person: bool = False
    layers: tuple[DemoLayer, ...] = field(default=())


# (hora, space, narrativa, razonamiento)
DAY: tuple[tuple[time, str, str, str], ...] = (
    (time(6, 40), "Kitchen",
     "Kitchen light's on. Someone's up before the alarm.",
     "Early for a weekday, but someone's always first up. Nothing unusual."),
    (time(7, 20), "Kitchen",
     "Breakfast happening. The usual three.",
     "Everyone at the table at the usual time. Just a normal morning."),
    (time(7, 48), "Kitchen",
     "Maya's off to school. Her jacket's still on the kitchen chair.",
     "Right on time for school. The jacket's the only thing out of place."),
    (time(8, 35), "Driveway",
     "Both cars gone. House is Luna's now.",
     "You both head out around now on weekdays. Luna's on her own, as usual."),
    (time(10, 10), "Living Room",
     "Luna hasn't moved off the couch in two hours.",
     "That's her spot. Long naps on the couch are what Luna does."),
    (time(11, 20), "Front Door",
     "A package arrived. It's sitting by the front door.",
     "Same van that comes most weeks, and they did exactly what they always do. "
     "Nothing worth flagging. I just figured you'd want to know there's a box outside."),
    (time(13, 5), "Living Room",
     "Quiet stretch. Nothing's moved since noon.",
     "Only Luna's home, and she's asleep. Exactly what a weekday looks like."),
    (time(15, 35), "Front Door",
     "Maya's back, and she brought a friend.",
     "Maya's home a little early, and not alone. Nothing seemed off, so I just noted it."),
    (time(16, 20), "Kitchen",
     "Both of them in the kitchen. The package made it inside.",
     "After-school snack. Someone brought the box in, so nothing's left outside."),
    (time(17, 40), "Front Door",
     "Maya's friend headed out.",
     "The friend left on their own, at an ordinary hour. Nothing to flag."),
    (time(18, 50), "Driveway",
     "First car's back in the driveway.",
     "Back right after work, like most evenings."),
    (time(19, 25), "Kitchen",
     "Everyone's home.",
     "Everyone who lives here is in. A normal evening."),
    (time(21, 40), "Living Room",
     "Living room's empty. Looks like the day's done.",
     "Lights out in the living room at the usual time. Quiet night ahead."),
)  # fmt: skip

PACKAGE_LAYERS: tuple[tuple[time, str], ...] = (
    (time(11, 19, 48), "A van stops in front of the house."),
    (time(11, 20, 12), "Someone walks up carrying a box."),
    (time(11, 20, 31), "They set it down by the door and leave."),
)

ATTENTION_AT = time(15, 35)
ATTENTION_NARRATIVE = "Maya's back with someone I haven't seen before."
ATTENTION_REASONING = (
    "Maya came home with someone I don't recognize. Nothing looked wrong, but I wanted you to know."
)


def demo_day(day: date, tz: ZoneInfo, attention: bool = False) -> list[DemoThread]:
    def at(t: time) -> datetime:
        return datetime.combine(day, t, tzinfo=tz)

    threads: list[DemoThread] = []
    for t, space, narrative, reasoning in DAY:
        start, end = at(t), at(t) + THREAD_LENGTH
        layers: tuple[DemoLayer, ...] = ()
        if t == time(11, 20):
            layers = tuple(DemoLayer(at(lt), text) for lt, text in PACKAGE_LAYERS)
            start, end = layers[0].captured_at, layers[-1].captured_at
        if attention and t == ATTENTION_AT:
            threads.append(
                DemoThread(
                    space, start, end, ATTENTION_NARRATIVE, ATTENTION_REASONING,
                    classification="attention", unfamiliar_person=True,
                )
            )  # fmt: skip
            continue
        threads.append(DemoThread(space, start, end, narrative, reasoning, layers=layers))
    return threads


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def seed(conn: asyncpg.Connection, bridge_token: str, attention: bool) -> int:
    tz = ZoneInfo(await conn.fetchval("select timezone from users where id = $1", USER_ID))
    bridge_id = await conn.fetchval(
        "select id from bridges where user_id = $1 order by created_at limit 1", USER_ID
    )
    if bridge_id is None:
        raise SystemExit("No bridge for user_lab. Apply supabase/lab_only first.")
    day = datetime.now(tz).date()
    day_start = datetime.combine(day, time(0), tzinfo=tz)

    async with conn.transaction():
        await conn.execute(
            """insert into bridge_secrets (bridge_id, token_hash) values ($1, $2)
               on conflict (bridge_id) do update set token_hash = excluded.token_hash""",
            bridge_id,
            token_hash(bridge_token),
        )

        space_ids: dict[str, object] = {}
        for name in SPACES:
            space_id = await conn.fetchval(
                "select id from spaces where user_id = $1 and name = $2", USER_ID, name
            )
            if space_id is None:
                space_id = await conn.fetchval(
                    """insert into spaces (user_id, bridge_id, name, status)
                       values ($1, $2, $3, 'active') returning id""",
                    USER_ID,
                    bridge_id,
                    name,
                )
            space_ids[name] = space_id

        # Rehace solo el día de hoy en los spaces de demo.
        await conn.execute(
            """delete from threads where user_id = $1 and space_id = any($2::uuid[])
               and start_time >= $3 and start_time < $4""",
            USER_ID,
            list(space_ids.values()),
            day_start,
            day_start + timedelta(days=1),
        )

        threads = demo_day(day, tz, attention)
        for th in threads:
            thread_id = await conn.fetchval(
                """insert into threads (user_id, space_id, status, narrative, classification,
                     reasoning, unfamiliar_person, start_time, end_time, last_layer_at)
                   values ($1, $2, 'closed', $3, $4, $5, $6, $7, $8, $8) returning id""",
                USER_ID,
                space_ids[th.space],
                th.narrative,
                th.classification,
                th.reasoning,
                th.unfamiliar_person,
                th.start_time,
                th.end_time,
            )
            for layer in th.layers:
                await conn.execute(
                    """insert into layers (user_id, thread_id, space_id, description, captured_at)
                       values ($1, $2, $3, $4, $5)""",
                    USER_ID,
                    thread_id,
                    space_ids[th.space],
                    layer.description,
                    layer.captured_at,
                )
    return len(threads)


async def run(attention: bool) -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        count = await seed(conn, os.environ["LAB_BRIDGE_TOKEN"], attention)
    finally:
        await conn.close()
    print(f"Seeded {count} threads for {USER_ID}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attention", action="store_true", help="3:35 PM thread as attention")
    asyncio.run(run(parser.parse_args().attention))


if __name__ == "__main__":
    main()
