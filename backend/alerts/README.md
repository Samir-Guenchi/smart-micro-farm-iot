# Telegram alert bot

Subscribes to the farm's MQTT topics and sends a Telegram message when
something needs attention. No app needed: alerts arrive on the farmer's phone.

| Alert | Fires when | Clears when |
|---|---|---|
| 🌱 Bed too dry | `soil_moisture_pct` stays below the threshold (25 %) for 30 min | moisture is back above threshold + 3 % |
| 🐔 Door still open | the coop door's last reported state is `open` 30 min after sunset (sunset computed from the farm's coordinates) | the door reports `closed`, or sunrise |
| 📡 Node offline | a node publishes `offline` (its MQTT last will) or sends nothing for 10 min | the node sends data or `online` again |
| 💧 Pump running too long | the pump runs past its requested `duration_s` + 2 min grace, or past 20 min when no duration was given | the pump stops |

Each condition sends **one** alert and stays quiet until it clears, then sends
one "resolved" message. No spam. All thresholds live in `config.toml`.

## Set up the Telegram bot (5 minutes)

1. In Telegram, open **@BotFather**, send `/newbot`, pick a name. Copy the token.
2. Send any message to your new bot (or add it to a family/farm group).
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy
   `"chat":{"id": ...}`. That number is the chat id (group ids start with `-`).

## Run

```bash
cd backend/alerts
cp config.example.toml config.toml        # set the farm's latitude/longitude and thresholds
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN=123456:ABC...   # from BotFather
export TELEGRAM_CHAT_ID=987654321
export MQTT_HOST=localhost MQTT_USER=greenloop MQTT_PASSWORD=...
python bot.py
```

Without `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` the bot still runs and only
logs the alerts, which is handy for testing.

With Docker, add this service next to the rest of the backend stack in
`backend/docker-compose.yml`:

```yaml
  alerts:
    build: ./alerts
    restart: unless-stopped
    depends_on: [mosquitto]
    environment:
      MQTT_HOST: mosquitto
      MQTT_USER: ${MQTT_USER}
      MQTT_PASSWORD: ${MQTT_PASSWORD}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
      ALERTS_CONFIG: /app/config.toml
    volumes:
      - ./alerts/config.toml:/app/config.toml:ro
```

## Try it without hardware

Run the simulator from `backend/` (issue #8), or publish by hand:

```bash
# Node offline
mosquitto_pub -t greenloop/coop-1/status -m offline -q 1 -u greenloop -P ...
# Door open (alerts once it is 30 min past sunset)
mosquitto_pub -t greenloop/coop-1/event -q 1 -m '{"type":"door","state":"open"}' -u greenloop -P ...
# Pump asked to run 60 s that never reports stopping (alerts after about 3 min)
mosquitto_pub -t greenloop/irrigation-1/event -q 1 -m '{"type":"pump","state":"started","duration_s":60}' -u greenloop -P ...
```

## Code

- `rules.py`: all alert logic, no MQTT or Telegram, fully unit tested.
- `sun.py`: sunrise/sunset from coordinates, no dependencies.
- `bot.py`: MQTT subscription, a 15 s evaluation loop and Telegram delivery.

```bash
python -m pytest -q
```
