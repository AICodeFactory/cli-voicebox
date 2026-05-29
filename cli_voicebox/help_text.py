"""Help text for argparse."""

from cli_voicebox.user_paths import get_config_path_help_lines


def build_main_epilog() -> str:
    config_section = "\n".join(get_config_path_help_lines())
    return f"""\
{config_section}

CONFIG JSON FIELDS (in config.json)
  voicebox_url       string  Voicebox server, default http://127.0.0.1:17493
  timeout_seconds    int     HTTP timeout for generation (default 600)

  Env overrides: VOICEBOX_BASE_URL, VOICEBOX_TIMEOUT
  Config path override: VOICEBOX_CLI_CONFIG=/path/to/config.json

VOICEBOX API (local REST, no API key)
  GET  /              Root
  GET  /health        Health check
  GET  /profiles      List voice profiles
  POST /generate      Text-to-speech generation
  GET  /audio/{{id}}   Download generated audio
  GET  /history       Generation history
  GET  /models/status Model catalog & load state

Docs: https://docs.voicebox.sh/api-reference

COMMON RESPONSE SCHEMA (stdout JSON)
  {{
    "status": "ok" | "failed",
    "data": <endpoint payload or null>,
    "msg": "<error message|null>",
    "audio_file": "<path when saved with -o on generate/audio>"
  }}

EXAMPLES
  voicebox-cli init
  voicebox-cli health
  voicebox-cli profiles
  voicebox-cli generate -t "Hello world" --profile-id <uuid> -o out.wav
  voicebox-cli audio --generation-id <uuid> -o out.wav
  voicebox-cli history --limit 10
"""

MAIN_DESCRIPTION = """\
voicebox-cli — call local Voicebox REST API (JSON in/out).

Subcommands:
  init      Create user config directory and config.json
  health    Check Voicebox server (GET /health, GET /)
  profiles  List voice profiles (GET /profiles)
  generate  Generate speech (POST /generate)
  audio     Download audio by generation id (GET /audio/{id})
  history   List generation history (GET /history)
  models    Model catalog & load state (GET /models/status)

Ensure Voicebox desktop app is running (default http://127.0.0.1:17493).
Stdout is a single JSON object unless --format text.
Exit codes: 0=success, 1=error.
"""

SUBCOMMAND_SUMMARY = {
    "init": "Create user config directory and config.json",
    "health": "Health check against Voicebox server",
    "profiles": "List all voice profiles",
    "generate": "Generate speech from text and optional profile",
    "audio": "Download generated audio file by generation id",
    "history": "List past generations",
    "models": "Show model catalog and load state",
}

GENERATE_DESCRIPTION = """\
Generate speech via POST /generate.

Requires profile_id (cloned or preset voice). List profiles with: voicebox-cli profiles
"""

GENERATE_EPILOG = """\
REQUEST
  Required:
    -t, --text TEXT           Text to synthesize
    --profile-id ID           Voice profile UUID (from profiles)

  Optional:
    --language CODE           e.g. en, zh (default from profile)
    --engine NAME             qwen|luxtts|kokoro|chatterbox|...
    --seed N                  Random seed
    --model-size SIZE         e.g. 1.7B, 0.6B
    --instruct TEXT           Delivery style (qwen_custom_voice)
    --max-chunk-chars N       Long-text chunk size (100-5000)
    --body-file FILE          Full JSON body (overrides individual flags)
    -o, --audio-out FILE      Save WAV/audio to file (fetches /audio/{{id}} if needed)
    --format json|text
    -c FILE                   Override config.json

RESPONSE (stdout JSON)
  status: "ok" | "failed"
  data: generation metadata from Voicebox
  audio_file: path when -o/--audio-out is used

EXAMPLES
  voicebox-cli generate -t "Hello" --profile-id <uuid>
  voicebox-cli generate -t "你好" --profile-id <uuid> --language zh -o hello.wav
  voicebox-cli generate --body-file request.json -o out.wav
"""
