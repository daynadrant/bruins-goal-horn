# Bruins Goal Horn

A Raspberry Pi goal horn for Boston Bruins games. The script polls the NHL's public scoreboard API, and whenever the Bruins' score goes up it flashes an LED and plays a goal-horn song for 77 seconds. A push button triggers the same celebration by hand.

## How it works

1. `main.py` requests `https://api-web.nhle.com/v1/score/now` every 5 seconds. The API is public and needs no key.
2. It finds the game involving `BOS`, reads the Bruins' score, and remembers it.
3. When the score is higher than on the previous poll, it starts a celebration in a background thread: the LED blinks every 0.5 s while `boston_audio.mp3` plays through pygame, for 77 seconds.
4. A button on GPIO 17 starts the same celebration manually. While one is running, new goals and presses are ignored.
5. `Ctrl+C` or `SIGTERM` stops the audio, turns the LED off and releases the GPIO pins.

If the GPIO libraries or hardware aren't available, the script falls back to a mock mode: it still polls the API and plays audio, but nothing is wired up. This is handy for testing on a laptop.

## Hardware

| Part | GPIO pin (BCM) |
| --- | --- |
| LED (with a resistor) | 18 |
| Push button (to ground, internal pull-up) | 17 |
| Speaker or audio output | via the Pi's audio out, played by pygame |

Pins use gpiozero with the `pigpio` pin factory. The pins, team, durations and polling interval are constants at the top of `main.py`.

## Setup

```bash
pip install -r requirements.txt
sudo pigpiod        # start the pigpio daemon (needed for the pigpio pin factory)
python main.py
```

On a Raspberry Pi OS install you may need `sudo apt install pigpio` first.

## Files

| File | Purpose |
| --- | --- |
| `main.py` | The goal monitor: API polling, LED and button handling, audio and shutdown |
| `boston_audio.mp3` | Goal song played during a celebration |
| `requirements.txt` | Python dependencies |

## Customizing

To follow another team, change `TEAM_NAME` and `TEAM_ABBREV` (the NHL's three-letter code, such as `TOR`) and swap in a different audio file via `AUDIO_FILE`.
