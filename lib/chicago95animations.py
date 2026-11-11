"""The animations the Control Panel's Effects tab offers (setup/animations.conf, which Setup reads too), the KWin
effects installed beside them, and what KDE does now while nothing is chosen."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

SPEED_KEY = "ANIM_SPEED"
GENERIC_SCRIPTED_SETTINGS = "kcm_kwin4_genericscripted"


@dataclass(frozen=True)
class Event:
    key: str
    label: str
    category: str | None
    group: str


@dataclass(frozen=True)
class Choice:
    value: str
    label: str
    effects: tuple[str, ...]  # KWin effect ids; "id/Flag" also needs kwinrc [Effect-id] Flag=true


@dataclass(frozen=True)
class Animations:
    events: tuple[Event, ...]
    choices: dict[str, tuple[Choice, ...]]
    classic: dict[str, dict[str, str]]
    unset: dict[str, str]


@dataclass(frozen=True)
class InstalledEffect:
    name: str
    category: str | None
    enabled_by_default: bool
    settings: tuple[str, ...] | None  # the command that opens its KDE settings page


@dataclass(frozen=True)
class EffectRoots:
    scripted: tuple[Path, ...]
    builtin: Path


DEFAULT_ROOTS = EffectRoots(
    scripted=(Path.home() / ".local/share/kwin/effects", Path("/usr/share/kwin/effects")),
    builtin=Path("/usr/share/kwin/builtin-effects"),
)


@dataclass(frozen=True)
class LiveState:
    kwinrc: dict[str, dict[str, str]]
    own: dict[str, str] = field(default_factory=dict)  # chicago95rc [Animations]: what Setup last chose
    speed: str | None = None  # kdeglobals AnimationDurationFactor


def read_animations(path):
    events, choices, classic, unset = [], {}, {}, {}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        kind, *fields = line.split("|")
        if kind == "EVENT":
            key, label, category, group = fields
            events.append(Event(key, label, None if category == "-" else category, group))
        elif kind == "CHOICE":
            key, value, label, effects = fields
            choices.setdefault(key, ())
            choices[key] += (Choice(value, label, tuple(effects.split())),)
        elif kind == "CLASSIC":
            look, key, value = fields
            classic.setdefault(look, {})[key] = value
        elif kind == "UNSET":
            key, value = fields
            unset[key] = value
    return Animations(tuple(events), choices, classic, unset)


def read_kde_config(path):
    """A KDE config file's groups and keys, case kept; lines without a value are skipped."""
    groups, current = {}, None
    for line in Path(path).read_text().splitlines() if Path(path).exists() else []:
        if line.startswith("[") and line.endswith("]"):
            current = groups.setdefault(line[1:-1], {})
        elif current is not None and "=" in line:
            key, value = line.split("=", 1)
            current[key] = value
    return groups


def settings_command(module):
    if not module:
        return None
    if module == GENERIC_SCRIPTED_SETTINGS:
        return ("kcmshell6", "kcm_kwin_effects")
    return ("kcmshell6", f"kwin/effects/configs/{module}")


def installed_effects(roots=DEFAULT_ROOTS):
    """Every effect KWin can load, by id: scripted ones (earlier roots win) and the built-in ones."""
    found = {}
    for root in roots.scripted:
        for metadata_path in sorted(Path(root).glob("*/metadata.json")):
            metadata = json.loads(metadata_path.read_text())
            plugin = metadata.get("KPlugin", {})
            effect_id = plugin.get("Id", metadata_path.parent.name)
            found.setdefault(
                effect_id,
                InstalledEffect(
                    plugin.get("Name", effect_id),
                    metadata.get("X-KWin-Exclusive-Category"),
                    bool(plugin.get("EnabledByDefault", False)),
                    settings_command(metadata.get("X-KDE-ConfigModule")),
                ),
            )
    for metadata_path in sorted(Path(roots.builtin).glob("*.json")):
        metadata = json.loads(metadata_path.read_text())
        effect = metadata.get("org.kde.kwin.effect", {})
        if effect.get("internal"):
            continue
        plugin = metadata.get("KPlugin", {})
        found.setdefault(
            metadata_path.stem,
            InstalledEffect(
                plugin.get("Name", metadata_path.stem),
                effect.get("exclusiveGroup"),
                bool(plugin.get("EnabledByDefault", False)),
                settings_command(metadata.get("X-KDE-ConfigModule")),
            ),
        )
    return found


def effect_id(token):
    return token.split("/")[0]


def event_of(table, key):
    return next(event for event in table.events if event.key == key)


def installed_extras(table, key, installed):
    """Installed effects of the event's category that none of its choices names, as (id, effect)."""
    category = event_of(table, key).category
    named = {effect_id(token) for choice in table.choices[key] for token in choice.effects}
    return [
        (installed_id, effect)
        for installed_id, effect in installed.items()
        if category and effect.category == category and installed_id not in named
    ]


def event_choices(table, key, installed):
    """The event's (label, value) choices: the file's, then the installed effects of its category by name."""
    return [(choice.label, choice.value) for choice in table.choices[key]] + [
        (effect.name, installed_id) for installed_id, effect in installed_extras(table, key, installed)
    ]


def choice_effects(table, key, value):
    """The effect tokens a choice turns on; a value that is no listed choice is an installed effect's id."""
    listed = {choice.value: choice.effects for choice in table.choices[key]}
    return listed.get(value, (value,))


def event_effects(table, key, installed):
    tokens = [token for choice in table.choices[key] for token in choice.effects]
    return {effect_id(token) for token in tokens} | {
        installed_id for installed_id, _ in installed_extras(table, key, installed)
    }


def token_active(token, installed, kwinrc):
    name, _, flag = token.partition("/")
    saved = kwinrc.get("Plugins", {}).get(f"{name}Enabled")
    enabled = (
        saved.lower() == "true" if saved is not None else (name in installed and installed[name].enabled_by_default)
    )
    return enabled and (not flag or kwinrc.get(f"Effect-{name}", {}).get(flag, "false").lower() == "true")


def nearest_speed(table, factor):
    return min(table.choices[SPEED_KEY], key=lambda choice: abs(float(choice.value) - float(factor))).value


def current_choice(table, key, installed, live):
    """What runs now: Setup's last choice, else the effects KWin has on, else the file's UNSET."""
    if key in live.own:
        return live.own[key]
    if key == SPEED_KEY:
        return nearest_speed(table, live.speed if live.speed is not None else table.unset[key])
    options = {value: choice_effects(table, key, value) for _, value in event_choices(table, key, installed)}
    tokens = {token for effects in options.values() for token in effects}
    if not tokens:
        return table.unset.get(key)
    active = {token for token in tokens if token_active(token, installed, live.kwinrc)}
    exact = [value for value, effects in options.items() if set(effects) == active]
    partial = [value for value, effects in options.items() if effects and set(effects) <= active]
    return (exact + partial + [table.unset.get(key)])[0]


def table_path():
    """Setup installs the table beside this module; a checkout keeps it in setup/."""
    beside = Path(__file__).with_name("animations.conf")
    return beside if beside.exists() else Path(__file__).resolve().parent.parent / "setup/animations.conf"


def live_state(config_dir=None):
    """What KDE and our tools are set to now: kwinrc, chicago95rc [Animations] and KDE's animation speed."""
    folder = Path(config_dir or os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    speed = read_kde_config(folder / "kdeglobals").get("KDE", {}).get("AnimationDurationFactor")
    return LiveState(
        read_kde_config(folder / "kwinrc"), read_kde_config(folder / "chicago95rc").get("Animations", {}), speed
    )


def own_animation(live, key, unset, duration_ms):
    """One of our tools' animations: the saved choice and its duration at KDE's speed; none when the speed is off."""
    duration = round(duration_ms * float(live.speed if live.speed is not None else 1))
    return (live.own.get(key, unset) if duration else "none", duration)
