import time
import requests
import pygame
import threading
import signal
import sys
from gpiozero import LED, Button
from gpiozero.pins.pigpio import PiGPIOFactory

# -------- CONFIGURATION --------
NHL_API_URL = "https://api-web.nhle.com/v1/score/now"

TEAM_NAME = "Bruins"
TEAM_ABBREV = "BOS"  # NHL uses team abbreviations
LED_PIN = 18
BUTTON_PIN = 17
AUDIO_FILE = "boston_audio.mp3"
GOAL_DURATION = 77
BLINK_INTERVAL = 0.5
POLL_INTERVAL = 5

# Global state
celebrating = False
shutdown_flag = False

# -------- PIGPIO FACTORY SETUP --------
try:
    factory = PiGPIOFactory()
    print("PiGPIO factory initialized successfully.")
except Exception as e:
    print(f"WARNING: Could not initialize PiGPIO factory: {e}")
    print("Falling back to default pin factory.")
    factory = None

# -------- GPIO INITIALIZATION --------
class MockGPIO:
    """Fallback mock GPIO for testing without hardware"""
    def __init__(self, pin=None, pull_up=False):
        self.pin = pin
        self.closed = False
    def on(self):
        pass
    def off(self):
        pass
    @property
    def is_pressed(self):
        return False
    def close(self):
        self.closed = True
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

def init_gpio():
    """Initialize GPIO with proper factory"""
    try:
        if factory:
            led = LED(LED_PIN, pin_factory=factory)
            manual_button = Button(BUTTON_PIN, pull_up=True, pin_factory=factory)
        else:
            led = LED(LED_PIN)
            manual_button = Button(BUTTON_PIN, pull_up=True)
        print(f"Hardware initialized: LED on GPIO {LED_PIN}, Button on GPIO {BUTTON_PIN}")
        return led, manual_button, True
    except Exception as e:
        print(f"GPIO initialization failed: {e}")
        print("Running in MOCK mode (no hardware control)")
        return MockGPIO(LED_PIN), MockGPIO(BUTTON_PIN, pull_up=True), False

led, manual_button, gpio_active = init_gpio()

# -------- PYGAME INITIALIZATION --------
try:
    pygame.mixer.init()
    print("Pygame mixer initialized successfully.")
except Exception as e:
    print(f"Pygame mixer initialization failed: {e}")

# -------- HARDWARE FUNCTIONS --------
def goal_celebration():
    """Blink LED and play horn/song for 77 seconds"""
    global celebrating
    
    if celebrating or shutdown_flag:
        return
    
    celebrating = True
    print("🏒 GOAL DETECTED! Starting celebration...")
    
    # Start audio playback
    audio_started = False
    try:
        pygame.mixer.music.load(AUDIO_FILE)
        pygame.mixer.music.play()
        audio_started = True
        print(f"Playing audio: {AUDIO_FILE}")
    except Exception as e:
        print(f"Audio Error: {e}")
    
    # LED blinking loop with shutdown checks
    start_time = time.time()
    try:
        while time.time() - start_time < GOAL_DURATION and not shutdown_flag:
            if gpio_active and not shutdown_flag:
                try:
                    led.on()
                    time.sleep(BLINK_INTERVAL / 2)
                    if not shutdown_flag:
                        led.off()
                        time.sleep(BLINK_INTERVAL / 2)
                except Exception as e:
                    print(f"LED control error: {e}")
                    break
            else:
                time.sleep(BLINK_INTERVAL)
    except Exception as e:
        print(f"Celebration loop error: {e}")
    
    # Cleanup
    if audio_started:
        try:
            pygame.mixer.music.stop()
        except:
            pass
    
    celebrating = False
    print("🎉 Celebration finished.")

def button_listener():
    """Monitor manual button press"""
    print("Button listener thread started")
    
    while not shutdown_flag:
        try:
            if gpio_active and manual_button.is_pressed and not celebrating:
                print("Manual button pressed!")
                threading.Thread(target=goal_celebration, daemon=True).start()
                time.sleep(1)  # Debounce
            time.sleep(0.05)
        except Exception as e:
            if not shutdown_flag:
                print(f"Button listener error: {e}")
            break
    
    print("Button listener thread stopped")

# -------- API FUNCTIONS --------
def fetch_bruins_score():
    """Fetch current Bruins score from NHL Official API"""
    try:
        response = requests.get(NHL_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # NHL API structure: data has "games" array
        games = data.get("games", [])
        
        if not games:
            return None, None, None
        
        # Find Bruins game
        bruins_game = None
        for game in games:
            home_abbrev = game.get("homeTeam", {}).get("abbrev", "")
            away_abbrev = game.get("awayTeam", {}).get("abbrev", "")
            
            if TEAM_ABBREV in [home_abbrev, away_abbrev]:
                bruins_game = game
                break
        
        if not bruins_game:
            return None, None, None
        
        # Get game state and scores
        game_state = bruins_game.get("gameState", "PRE")
        home_team = bruins_game.get("homeTeam", {})
        away_team = bruins_game.get("awayTeam", {})
        
        # Determine which side Bruins are on
        if home_team.get("abbrev") == TEAM_ABBREV:
            bruins_score = home_team.get("score", 0)
            opponent = away_team.get("abbrev", "OPP")
        else:
            bruins_score = away_team.get("score", 0)
            opponent = home_team.get("abbrev", "OPP")
        
        # Create status string
        status = game_state
        if game_state == "LIVE" or game_state == "CRIT":
            period = bruins_game.get("period", 1)
            clock = bruins_game.get("clock", {}).get("timeRemaining", "")
            status = f"P{period} {clock}"
        
        teams_info = {
            "opponent": opponent,
            "game_state": game_state
        }
        
        return bruins_score, status, teams_info
    
    except requests.exceptions.Timeout:
        print("NHL API request timed out")
    except requests.exceptions.RequestException as e:
        print(f"NHL API request error: {e}")
    except KeyError as e:
        print(f"Score parsing error - missing key: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return None, None, None

# -------- GRACEFUL SHUTDOWN --------
def cleanup_and_exit(signum=None, frame=None):
    """Handle graceful shutdown"""
    global shutdown_flag
    
    if shutdown_flag:
        return
    
    shutdown_flag = True
    print("\nShutting down gracefully...")
    
    # Stop audio
    try:
        pygame.mixer.music.stop()
    except:
        pass
    
    # Close GPIO
    try:
        if gpio_active:
            led.off()
            led.close()
            manual_button.close()
            print("GPIO devices closed")
    except Exception as e:
        print(f"GPIO cleanup warning: {e}")
    
    # Close pigpio factory
    try:
        if factory:
            factory.close()
            print("PiGPIO factory closed")
    except:
        pass
    
    print("Application fully closed.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

# -------- MAIN LOOP --------
def main():
    print("=" * 50)
    print("🏒 BRUINS GOAL MONITOR STARTING 🏒")
    print("=" * 50)
    print(f"Monitoring team: {TEAM_NAME} ({TEAM_ABBREV})")
    print(f"Using: NHL Official API")
    print(f"Poll interval: {POLL_INTERVAL} seconds")
    print(f"GPIO Active: {gpio_active}")
    print("=" * 50)
    
    last_bruins_score = None
    
    # Start button listener thread
    button_thread = threading.Thread(target=button_listener, daemon=True)
    button_thread.start()
    
    while not shutdown_flag:
        try:
            if celebrating:
                time.sleep(POLL_INTERVAL)
                continue
            
            current_score, status, teams = fetch_bruins_score()
            
            if current_score is None:
                print("No Bruins game found or NHL API unavailable")
            else:
                # Initialize tracking when game starts
                if last_bruins_score is None:
                    last_bruins_score = current_score
                    opponent = teams.get("opponent", "OPP") if teams else "OPP"
                    print(f"Game found! BOS vs {opponent}, Status: {status}, Score: {current_score}")
                
                # Detect goals
                elif current_score > last_bruins_score:
                    print(f"\n🚨 GOAL! Score changed: {last_bruins_score} → {current_score} 🚨\n")
                    threading.Thread(target=goal_celebration, daemon=True).start()
                    last_bruins_score = current_score
                else:
                    print(f"[{status}] Bruins: {current_score}")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Main loop error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_and_exit()