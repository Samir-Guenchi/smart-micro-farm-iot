"""Alert rules for GreenLoop Farm, kept free of MQTT and Telegram so they can be tested.

Feed messages in with on_telemetry / on_status / on_event, call tick(now)
regularly, and each call returns the alerts to send. Every condition fires
once and then stays quiet until it clears, when a single "resolved" message
is returned.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sun import sun_times


@dataclass
class Alert:
    key: str
    text: str
    resolved: bool = False


@dataclass
class Config:
    latitude: float
    longitude: float
    dry_threshold_pct: float = 25.0
    dry_minutes: float = 30
    dry_clear_margin_pct: float = 3.0
    door_node: str = "coop-1"
    door_minutes_after_sunset: float = 30
    offline_minutes: float = 10
    nodes: list = field(default_factory=lambda: ["irrigation-1", "hive-1", "coop-1"])
    pump_max_minutes: float = 20
    pump_grace_minutes: float = 2

    @classmethod
    def from_toml(cls, data):
        farm, dry, door = data["farm"], data.get("dry_bed", {}), data.get("door", {})
        offline, pump = data.get("offline", {}), data.get("pump", {})
        defaults = cls(latitude=0, longitude=0)
        return cls(
            latitude=farm["latitude"],
            longitude=farm["longitude"],
            dry_threshold_pct=dry.get("threshold_pct", defaults.dry_threshold_pct),
            dry_minutes=dry.get("minutes", defaults.dry_minutes),
            dry_clear_margin_pct=dry.get("clear_margin_pct", defaults.dry_clear_margin_pct),
            door_node=door.get("node", defaults.door_node),
            door_minutes_after_sunset=door.get("minutes_after_sunset", defaults.door_minutes_after_sunset),
            offline_minutes=offline.get("minutes", defaults.offline_minutes),
            nodes=offline.get("nodes", defaults.nodes),
            pump_max_minutes=pump.get("max_minutes", defaults.pump_max_minutes),
            pump_grace_minutes=pump.get("grace_minutes", defaults.pump_grace_minutes),
        )


def _fmt_time(dt):
    return dt.astimezone().strftime("%H:%M")


class Rules:
    def __init__(self, config: Config, now: datetime):
        self.cfg = config
        self.active = set()  # keys of alerts that fired and have not cleared
        self.started = now  # don't call nodes offline before they had a chance to report
        self.last_seen = {}
        self.status = {}
        self.soil = {}
        self.dry_since = {}
        self.door_state = None
        self.pump_since = {}
        self.pump_expected_s = {}

    # Inputs ---------------------------------------------------------------

    def on_telemetry(self, node, metrics, now):
        self.last_seen[node] = now
        if "soil_moisture_pct" in metrics:
            value = float(metrics["soil_moisture_pct"])
            self.soil[node] = value
            if value < self.cfg.dry_threshold_pct:
                self.dry_since.setdefault(node, now)
            else:
                self.dry_since.pop(node, None)
        if "pump_on" in metrics:
            if int(metrics["pump_on"]):
                self.pump_since.setdefault(node, now)
            else:
                self._pump_stopped(node)

    def on_status(self, node, status, now):
        self.status[node] = status
        if status == "online":
            self.last_seen[node] = now

    def on_event(self, node, event, now):
        self.last_seen[node] = now
        kind, state = event.get("type"), event.get("state")
        if kind == "door" and node == self.cfg.door_node:
            self.door_state = state
        elif kind == "pump":
            if state == "started":
                self.pump_since[node] = now
                if event.get("duration_s"):
                    self.pump_expected_s[node] = float(event["duration_s"])
            elif state == "stopped":
                self._pump_stopped(node)

    def _pump_stopped(self, node):
        self.pump_since.pop(node, None)
        self.pump_expected_s.pop(node, None)

    # Evaluation -----------------------------------------------------------

    def tick(self, now):
        alerts = []
        alerts += self._check_dry(now)
        alerts += self._check_door(now)
        alerts += self._check_offline(now)
        alerts += self._check_pump(now)
        return alerts

    def _set(self, key, condition, fire_text, clear_text):
        """Returns an Alert only on a change of state, which is what stops alert spam."""
        if condition and key not in self.active:
            self.active.add(key)
            return [Alert(key, fire_text)]
        if not condition and key in self.active:
            self.active.discard(key)
            return [Alert(key, clear_text, resolved=True)]
        return []

    def _check_dry(self, now):
        out = []
        for node, value in self.soil.items():
            key = f"dry:{node}"
            since = self.dry_since.get(node)
            too_long = since is not None and now - since >= timedelta(minutes=self.cfg.dry_minutes)
            if key in self.active:
                # Hysteresis: stay active until clearly wet again, so readings hovering at the threshold don't flap.
                condition = value < self.cfg.dry_threshold_pct + self.cfg.dry_clear_margin_pct
            else:
                condition = too_long
            out += self._set(
                key,
                condition,
                f"🌱 Bed too dry on {node}: soil moisture {value:.0f}% "
                f"(below {self.cfg.dry_threshold_pct:.0f}% for over {self.cfg.dry_minutes:.0f} min).",
                f"✅ {node} soil moisture back to {value:.0f}%.",
            )
        return out

    def _night_window(self, now):
        """Returns (sunset, deadline) if now is between deadline (sunset + margin) and the next sunrise."""
        for offset in (-1, 0):
            day = now.date() + timedelta(days=offset)
            _, sunset = sun_times(day, self.cfg.latitude, self.cfg.longitude)
            sunrise, _ = sun_times(day + timedelta(days=1), self.cfg.latitude, self.cfg.longitude)
            if sunset is None or sunrise is None:
                continue
            deadline = sunset + timedelta(minutes=self.cfg.door_minutes_after_sunset)
            if deadline <= now < sunrise:
                return sunset, deadline
        return None, None

    def _check_door(self, now):
        sunset, _ = self._night_window(now)
        # Only a door known to be open counts; with no report yet there is nothing to act on.
        condition = sunset is not None and self.door_state == "open"
        clear = "✅ Coop door is closed." if self.door_state == "closed" else "☀️ Morning: door alert reset."
        fire = (
            f"🐔 Coop door is still open, {self.cfg.door_minutes_after_sunset:.0f} min after sunset ({_fmt_time(sunset)})."
            if sunset
            else ""
        )
        return self._set("door", condition, fire, clear)

    def _check_offline(self, now):
        out = []
        limit = timedelta(minutes=self.cfg.offline_minutes)
        for node in self.cfg.nodes:
            last = self.last_seen.get(node, self.started)
            silent = now - last >= limit
            condition = self.status.get(node) == "offline" or silent
            if self.status.get(node) == "offline":
                why = "reported offline"
            elif node in self.last_seen:
                why = f"no data since {_fmt_time(last)}"
            else:
                why = f"no data for {self.cfg.offline_minutes:.0f} min"
            out += self._set(f"offline:{node}", condition, f"📡 Node {node} is offline ({why}).", f"✅ Node {node} is back online.")
        return out

    def _check_pump(self, now):
        out = []
        for node in set(self.pump_since) | {k.split(":", 1)[1] for k in self.active if k.startswith("pump:")}:
            since = self.pump_since.get(node)
            expected_s = self.pump_expected_s.get(node, self.cfg.pump_max_minutes * 60)
            limit = timedelta(seconds=expected_s) + timedelta(minutes=self.cfg.pump_grace_minutes)
            running = since is not None and now - since >= limit
            minutes = (now - since).total_seconds() / 60 if since else 0
            out += self._set(
                f"pump:{node}",
                running,
                f"💧 Pump on {node} has been running for {minutes:.0f} min "
                f"(expected about {expected_s / 60:.0f} min). Check for a stuck relay or leak.",
                f"✅ Pump on {node} has stopped.",
            )
        return out


def utcnow():
    return datetime.now(timezone.utc)
