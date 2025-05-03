# -*- coding: utf-8 -*-
import sqlite3
import sys
import os
import json
import platform

# --- Default Configuration ---
DEFAULT_MAX_MATCHES = 3
CONFIG_FILENAME = "lyrics-search.conf"

# --- Variables for loaded/current configuration ---
current_db_path = None
current_max_matches = DEFAULT_MAX_MATCHES
config_file_path = ""
config_available = False # Flag indicating if configuration was (at least partially) loaded

# --- Configuration for DB Schema (Adjust to your schema!) ---
TRACKS_TABLE = "tracks"
TRACK_ID_COL = "id"
TRACK_TITLE_COL = "name"
TRACK_ARTIST_COL = "artist_name"

LYRICS_TABLE = "lyrics"
LYRICS_FK_COL = "track_id"
LYRICS_TEXT_COL = "plain_lyrics"

FTS_TABLE = "tracks_fts"
# -------------------------------------------------------------------

# --- ASCII Art Banner ---
ascii_art_banner = r"""

  _                _             _____                     _
 | |              (_)           / ____|                   | |
 | |    _   _ _ __ _  ___ ___  | (___   ___  __ _ _ __ ___| |__
 | |   | | | | '__| |/ __/ __|  \___ \ / _ \/ _` | '__/ __| '_ \
 | |___| |_| | |  | | (__\__ \  ____) |  __/ (_| | | | (__| | | |
 |______\__, |_|  |_|\___|___/ |_____/ \___|\__,_|_|  \___|_| |_|
         __/ |
        |___/

"""
# -------------------------

# --- Placeholder Texts for Instructions ---
db_instructions_text = """
--- Instructions: Get Database ---

To obtain the database required for this program, go to https://lrclib.net/db-dumps and download the latest .gz file.
Then unzip the .gz file to a .sqlite3 file.
Then select the setup option in this program and enter the path to this .sqlite3 file.
"""

lookup_instructions_text = """
--- Instructions: Use 'lookup' ---

With the lookup argument you can find lyrics faster to use them in other programs.

Use it like this:
  python {script_name} lookup “search query”

The output is the first result that is found, together with the song name, artist name and lyrics. The output is formatted as JSON.
"""
# ------------------------------------

def clear_screen():
    """Clears the terminal screen OS-independently."""
    os_name = platform.system()
    if os_name == "Windows":
        os.system('cls')
    else: # Linux, macOS, etc.
        os.system('clear')

# --- Configuration Functions ---
def get_config_path():
    """Determines the path to the configuration file in the script directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, CONFIG_FILENAME)

def load_config():
    """Loads the configuration from the file."""
    global current_db_path, current_max_matches, config_file_path, config_available
    config_file_path = get_config_path()
    config_available = False # Reset flag

    # Reset to defaults in case the file doesn't exist or is faulty
    current_db_path = None
    current_max_matches = DEFAULT_MAX_MATCHES

    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                temp_db_path = None
                temp_max_matches = DEFAULT_MAX_MATCHES

                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): # Ignore comments/empty lines
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'db_path':
                            # Just store the path, existence checked upon use
                            temp_db_path = value
                        elif key == 'max_matches':
                            try:
                                val_int = int(value)
                                if val_int > 0:
                                    temp_max_matches = val_int
                                else:
                                     # Quietly ignore invalid values during load, use default
                                     pass
                                     # print(f"WARNING: Invalid value for max_matches ({value}) in '{CONFIG_FILENAME}', using default ({DEFAULT_MAX_MATCHES}).", file=sys.stderr)
                            except ValueError:
                                 # Quietly ignore invalid values during load
                                 pass
                                 # print(f"WARNING: Invalid value for max_matches ('{value}') in '{CONFIG_FILENAME}', using default ({DEFAULT_MAX_MATCHES}).", file=sys.stderr)

                # Update global variables only if values were found
                current_db_path = temp_db_path
                current_max_matches = temp_max_matches
                # Config is considered available if the file exists (even if path is invalid)
                config_available = True

        except IOError as e:
            print(f"ERROR reading config '{config_file_path}': {e}", file=sys.stderr)
        except Exception as e:
            print(f"ERROR processing config '{config_file_path}': {e}", file=sys.stderr)

    # config_available remains False if the file doesn't exist or a read error occurred
    return config_available

def save_config(db_path, max_matches):
    """Saves the configuration to the file."""
    global config_file_path, config_available
    config_file_path = get_config_path()
    try:
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Configuration file for Lyric Search Tool\n")
            if db_path:
                f.write(f"db_path={db_path}\n")
            f.write(f"max_matches={max_matches}\n")
        # Use stderr for info messages in case stdout is used by lookup
        print(f"INFO: Configuration saved to '{config_file_path}'", file=sys.stderr)
        config_available = True # Config is available after successful save
        return True
    except IOError as e:
        print(f"ERROR saving configuration to '{config_file_path}': {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR saving configuration: {e}", file=sys.stderr)
        return False

# --- Interactive Mode: Setup ---
def run_setup():
    """Runs the setup process (asks for path and max matches)."""
    global current_db_path, current_max_matches
    clear_screen()
    print("--- Setup ---")

    new_db_path = ""
    while True:
        prompt = f"Enter path to the SQLite database file"
        if current_db_path:
            prompt += f" (current: {current_db_path})"
        prompt += ": "
        user_input = input(prompt).strip()

        if not user_input and current_db_path:
            # Keep current path if nothing is entered
            new_db_path = current_db_path
            break
        elif user_input:
            # Check if the entered path exists and is a file
            if os.path.exists(user_input) and os.path.isfile(user_input):
                new_db_path = user_input
                break
            else:
                print(f"ERROR: File not found: '{user_input}'. Please try again.")
        else:
             print("ERROR: Database path cannot be empty if none is set.")

    new_max_matches = current_max_matches # Start with current/default value
    while True:
        prompt = f"Enter maximum number of results (Default: {DEFAULT_MAX_MATCHES}, current: {current_max_matches}): "
        user_input = input(prompt).strip()
        if not user_input:
            # Keep current value on empty input
            new_max_matches = current_max_matches
            break
        else:
            try:
                val_int = int(user_input)
                if val_int > 0:
                    new_max_matches = val_int
                    break
                else:
                    print("ERROR: Number must be greater than 0.")
            except ValueError:
                print("ERROR: Please enter a valid number.")

    # Save and update global variables
    if save_config(new_db_path, new_max_matches):
        current_db_path = new_db_path
        current_max_matches = new_max_matches
        print("Setup completed successfully.")
    else:
        print("Setup could not be saved.")

    wait_for_enter("[ Press Enter to return to menu ]")


# --- Interactive Mode: Display ---
def display_main_menu():
    """Displays the main menu with the new order."""
    print("--- Main Menu ---")
    print("1: Search Lyrics")
    print("2: Setup")
    print("3: Get Database (Instructions)")
    print("4: Use 'lookup' (Instructions)")
    print("5: Exit Program")
    print("-----------------")

def wait_for_enter(message="[ Press Enter to return to menu ]"):
    """Waits for the user to press Enter."""
    try:
        input(f"\n{message}")
    except (EOFError, KeyboardInterrupt):
        print("\nAction cancelled.") # General message

def display_results(found_tracks):
    """Displays the found tracks and lyrics formatted."""
    if not found_tracks:
        print("\nNo matching tracks found.")
        return

    # Use current_max_matches for display info, not the actual count
    print(f"\nTop {len(found_tracks)} relevant tracks (max {current_max_matches}) and their lyrics:")
    print("=" * 40)
    for i, track in enumerate(found_tracks):
        track_id = track.get(TRACK_ID_COL, 'N/A')
        title = track.get(TRACK_TITLE_COL, 'N/A')
        artist = track.get(TRACK_ARTIST_COL, 'N/A')
        lyrics_text = track.get(LYRICS_TEXT_COL)

        print(f"Track {i + 1} (ID: {track_id})")
        print(f"  Title:  {title}")
        print(f"  Artist: {artist}")
        print("-" * 20)
        print("  Lyrics:")

        if 'error' in track:
             print(f"    Error loading ({track['error']})") # Slightly indented
        elif lyrics_text is not None:
            for line in lyrics_text.splitlines():
                print(f"    {line}") # Indent with 4 spaces
            # Handle empty lyrics (string of length 0) correctly
            if not lyrics_text:
                print("    (Empty)")
        else:
            print("    Not available (or column empty)") # Slightly indented
        print("=" * 40) # Separator line after each track


# --- Core Search Function ---
def search_tracks_and_lyrics(db_path, query, max_matches_limit):
    """Searches the DB and returns a list of dictionaries or None on error."""
    if not db_path or not os.path.exists(db_path):
        print(f"ERROR: Database path '{db_path}' invalid or not set.", file=sys.stderr)
        return None # Signal DB path problem

    results = []
    conn = None
    try:
        # print(f"INFO: Connecting to database: {db_path}", file=sys.stderr) # Keep quiet for lookup
        db_uri = f'file:{db_path}?mode=ro'
        try:
            conn = sqlite3.connect(db_uri, uri=True)
        except sqlite3.OperationalError:
            # print("WARNING: Could not open in read-only mode, trying normal mode.", file=sys.stderr)
            conn = sqlite3.connect(db_path)

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # print(f"INFO: Searching for top {max_matches_limit} tracks matching: '{query}'...", file=sys.stderr)

        fts_sql = f"""
            SELECT rowid
            FROM "{FTS_TABLE}"
            WHERE "{FTS_TABLE}" MATCH ?
            ORDER BY rank
            LIMIT ?;
        """
        try:
            cursor.execute(fts_sql, (query, max_matches_limit))
            top_track_ids = [row['rowid'] for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
             print(f"ERROR executing FTS search on table '{FTS_TABLE}': {e}", file=sys.stderr)
             return None # Signal FTS error

        if not top_track_ids:
            # print("INFO: No matching tracks found via FTS.", file=sys.stderr)
            return [] # Empty list = not found

        # print(f"INFO: Found {len(top_track_ids)} relevant track IDs: {top_track_ids}", file=sys.stderr)
        # print(f"INFO: Fetching details and lyrics for these tracks...", file=sys.stderr)

        placeholders = ', '.join('?' * len(top_track_ids))
        details_sql = f"""
            SELECT
                t."{TRACK_ID_COL}",
                t."{TRACK_TITLE_COL}",
                t."{TRACK_ARTIST_COL}",
                l."{LYRICS_TEXT_COL}"
            FROM "{TRACKS_TABLE}" AS t
            LEFT JOIN "{LYRICS_TABLE}" AS l ON t."{TRACK_ID_COL}" = l."{LYRICS_FK_COL}"
            WHERE t."{TRACK_ID_COL}" IN ({placeholders});
        """
        try:
            cursor.execute(details_sql, top_track_ids)
            fetched_results = cursor.fetchall()
            results_map = {row[TRACK_ID_COL]: dict(row) for row in fetched_results}
            for track_id in top_track_ids:
                 if track_id in results_map:
                     results.append(results_map[track_id])
                 else: # Should not happen with LEFT JOIN unless ID was wrong
                    # print(f"WARNING: Could not find details for Track ID {track_id} although it was in FTS index.", file=sys.stderr)
                    results.append({TRACK_ID_COL: track_id, 'error': f'Details for ID {track_id} not found'})

        except sqlite3.OperationalError as e:
            print(f"ERROR fetching track/lyric details: {e}", file=sys.stderr)
            # Return only error objects so lookup mode can report this
            return [{'error': f'SQL error fetching details: {e}'} for _ in top_track_ids]

        # print("INFO: Search completed successfully.", file=sys.stderr)
        return results

    except sqlite3.Error as e:
        print(f"ERROR: SQLite error: {e}", file=sys.stderr)
        return None # Signal general DB error
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        return None # Signal unexpected error
    finally:
        if conn:
            conn.close()
            # print("INFO: Database connection closed.", file=sys.stderr)


# --- Main Function for Interactive Mode ---
def main_interactive():
    """Controls the interactive menu flow."""
    # Config was already loaded in __main__

    while True:
        # --- Screen setup for each menu display ---
        clear_screen()
        print(ascii_art_banner)
        if current_db_path:
             print(f"Current Database: {current_db_path}")
        else:
             print("Current Database: --- Not Set ---")
        print(f"Max Results: {current_max_matches}")
        # Show hint only if config file is missing OR the path from it is invalid/not set
        if not config_available or not current_db_path:
            print("\n*** NOTE: Setup has not been (fully) completed! ***")
            print("*** Please select option 2 (Setup) to configure the database. ***")
        # **************************************************

        display_main_menu() # Displays the menu with the NEW order
        choice = input("Enter a number: ")

        # --- Logic adapted to the NEW menu order ---
        if choice == '1': # Search Lyrics (unchanged)
            if not current_db_path:
                clear_screen(); print("ERROR: No database path configured."); print("Please run Setup (Option 2) first."); wait_for_enter(); continue
            try:
                clear_screen(); print("--- Search Lyrics ---")
                search_query = input("Search term: ")
                if not search_query: print("No search term entered."); wait_for_enter(); continue
                # Call search with current config values
                found_tracks = search_tracks_and_lyrics(current_db_path, search_query, current_max_matches)
                clear_screen()
                if found_tracks is None: print("\nAn error occurred during the search. Details above.")
                else: display_results(found_tracks)
                wait_for_enter() # Wait after displaying results
            except (KeyboardInterrupt, EOFError): clear_screen(); print("\nSearch cancelled."); wait_for_enter(); continue

        elif choice == '2': # Setup (was 4)
            run_setup()
            # Loop continues -> Clear + Banner + Menu on next iteration

        elif choice == '3': # DB Instructions (was 3)
            clear_screen(); print(db_instructions_text); wait_for_enter()
            # Loop continues -> Clear + Banner + Menu

        elif choice == '4': # Lookup Instructions (new)
            clear_screen()
            script_name = os.path.basename(sys.argv[0])
            print(lookup_instructions_text.format(script_name=script_name))
            wait_for_enter()
            # Loop continues -> Clear + Banner + Menu

        elif choice == '5': # Exit Program (was 2, then 4)
            clear_screen(); print("Exiting program."); sys.exit(0)
        # *******************************************

        else: # Invalid choice
            clear_screen(); print("Invalid choice. Please enter 1, 2, 3, 4, or 5."); wait_for_enter()
            # Loop continues -> Clear + Banner + Menu

# --- Main Function for Lookup Mode ---
def main_lookup(search_term):
    """Performs a single search and prints JSON output."""
    # Config was already loaded in __main__
    if not current_db_path:
        print(json.dumps({"error": "Configuration error: Database path not set"}), file=sys.stdout)
        sys.exit(1)
    if not os.path.exists(current_db_path):
         print(json.dumps({"error": f"Configuration error: Database file not found at '{current_db_path}'"}), file=sys.stdout)
         sys.exit(1)


    # Perform search for exactly 1 result
    found_tracks = search_tracks_and_lyrics(current_db_path, search_term, 1)

    if found_tracks is None:
        # Serious search error (DB problem, FTS problem, etc.)
        print(json.dumps({"error": "Search execution failed"}), file=sys.stdout)
        sys.exit(1)
    elif not found_tracks:
        # No results found
        print(json.dumps({"error": "No matching track found"}), file=sys.stdout)
        sys.exit(0) # Not an error per se, just no result
    elif 'error' in found_tracks[0]:
         # Error fetching details AFTER successful FTS search
         print(json.dumps({"error": found_tracks[0]['error']}), file=sys.stdout)
         sys.exit(1)
    else:
        # Successful result
        track_data = found_tracks[0]
        result_json = {
            "name": track_data.get(TRACK_TITLE_COL),
            "artist_name": track_data.get(TRACK_ARTIST_COL),
            "plain_lyrics": track_data.get(LYRICS_TEXT_COL) # Remains None if not available
        }
        # Print JSON to stdout, compact for APIs
        print(json.dumps(result_json, ensure_ascii=False, separators=(',', ':')), file=sys.stdout)
        sys.exit(0)


# --- Entry Point ---
if __name__ == "__main__":
    # Load configuration *once* at the start
    load_config()

    # Decide mode based on arguments
    if len(sys.argv) == 1:
        # No arguments -> Interactive Mode
        main_interactive()
    elif len(sys.argv) == 3 and sys.argv[1].lower() == 'lookup':
        # Argument 'lookup' + search term -> Lookup Mode
        search_term_arg = sys.argv[2]
        main_lookup(search_term_arg)
    else:
        # Incorrect or incomplete arguments
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage:", file=sys.stderr)
        print(f"  Interactive mode: python {script_name}", file=sys.stderr)
        print(f"  Lookup mode:      python {script_name} lookup \"<search_term>\"", file=sys.stderr)
        sys.exit(1)