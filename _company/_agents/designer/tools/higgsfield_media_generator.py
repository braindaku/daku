import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys


CONFIG_FILENAME = "higgsfield_media_generator.json"


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def now_string():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def str_to_bool(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_key_value_items(items):
    parsed = {}

    if not items:
        return parsed

    for item in items:
        if "=" not in item:
            raise ValueError(f"추가 옵션 형식이 올바르지 않습니다: {item}. 예: --extra quality=high")

        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not re.match(r"^[A-Za-z0-9_-]+$", key):
            raise ValueError(f"허용되지 않는 옵션 이름입니다: {key}")

        parsed[key] = value

    return parsed


def add_option(command, option_name, value):
    if value is None:
        return

    if isinstance(value, str) and value.strip() == "":
        return

    if isinstance(value, bool):
        if value:
            command.append(f"--{option_name}")
        return

    command.extend([f"--{option_name}", str(value)])


def find_urls(text):
    if not text:
        return []

    pattern = r"https?://[^\s\"'<>]+"
    urls = re.findall(pattern, text)
    unique_urls = []

    for url in urls:
        cleaned = url.rstrip(".,)]}")
        if cleaned not in unique_urls:
            unique_urls.append(cleaned)

    return unique_urls


def parse_stdout(stdout):
    if not stdout:
        return None

    stripped = stdout.strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def resolve_cli_binary(cli_bin):
    if not cli_bin:
        cli_bin = "higgsfield"

    has_path_separator = os.sep in cli_bin or (os.altsep and os.altsep in cli_bin)

    if has_path_separator:
        if os.path.exists(cli_bin):
            return cli_bin
        raise FileNotFoundError(f"Higgsfield CLI 실행 파일을 찾을 수 없습니다: {cli_bin}")

    resolved = shutil.which(cli_bin)

    if not resolved:
        raise FileNotFoundError(
            "Higgsfield CLI를 찾을 수 없습니다. "
            "먼저 `npm install -g @higgsfield/cli`를 실행하고, "
            "`higgsfield auth login`으로 로그인하세요."
        )

    return resolved


def build_generate_command(config, args):
    cli_bin = resolve_cli_binary(args.cli_bin or config.get("HIGGSFIELD_CLI_BIN", "higgsfield"))

    generation_type = args.type or config.get("GENERATION_TYPE", "image")
    generation_type = generation_type.strip().lower()

    if generation_type not in {"image", "video"}:
        raise ValueError("GENERATION_TYPE은 'image' 또는 'video'여야 합니다.")

    prompt = args.prompt or config.get("PROMPT", "")
    if not prompt:
        raise ValueError(
            f"생성 프롬프트가 비어 있습니다. PROMPT 또는 --prompt 값을 입력하세요. "
            f"(args.prompt: {repr(args.prompt)}, config keys: {list(config.keys()) if config else None}, config PROMPT: {repr(config.get('PROMPT')) if config else None})"
        )

    if args.model:
        model = args.model
    elif generation_type == "image":
        model = config.get("IMAGE_MODEL", "nano_banana_2")
    else:
        model = config.get("VIDEO_MODEL", "kling3_0")

    action = args.action or "create"
    if action not in {"create", "cost"}:
        raise ValueError("지원하는 생성 액션은 'create' 또는 'cost'입니다.")

    command = [cli_bin, "generate", action, model, "--prompt", prompt]

    aspect_ratio = args.aspect_ratio if args.aspect_ratio is not None else config.get("ASPECT_RATIO", "")
    resolution = args.resolution if args.resolution is not None else config.get("RESOLUTION", "")

    add_option(command, "aspect_ratio", aspect_ratio)
    add_option(command, "resolution", resolution)

    if generation_type == "video":
        duration = args.duration if args.duration is not None else config.get("DURATION", "")
        mode = args.mode if args.mode is not None else config.get("MODE", "")
        sound = args.sound if args.sound is not None else config.get("SOUND", "")
        start_image = args.start_image if args.start_image is not None else config.get("START_IMAGE", "")

        add_option(command, "duration", duration)
        add_option(command, "mode", mode)
        add_option(command, "sound", sound)
        add_option(command, "start-image", start_image)

    config_extra_args = config.get("EXTRA_ARGS", {})
    if config_extra_args is None:
        config_extra_args = {}

    if not isinstance(config_extra_args, dict):
        raise ValueError("EXTRA_ARGS는 JSON 객체 형식이어야 합니다.")

    cli_extra_args = parse_key_value_items(args.extra)
    merged_extra_args = {**config_extra_args, **cli_extra_args}

    protected_options = {
        "prompt",
        "aspect_ratio",
        "resolution",
        "duration",
        "mode",
        "sound",
        "start-image",
        "wait",
        "wait-timeout",
        "wait-interval",
        "json",
        "no-color"
    }

    for key, value in merged_extra_args.items():
        normalized_key = str(key).strip()
        if normalized_key in protected_options:
            continue
        if not re.match(r"^[A-Za-z0-9_-]+$", normalized_key):
            raise ValueError(f"허용되지 않는 EXTRA_ARGS 옵션 이름입니다: {normalized_key}")
        add_option(command, normalized_key, value)

    wait_for_result = str_to_bool(config.get("WAIT_FOR_RESULT", True))
    if args.wait:
        wait_for_result = True
    if args.no_wait:
        wait_for_result = False

    if action == "create" and wait_for_result:
        command.append("--wait")
        wait_timeout = args.wait_timeout if args.wait_timeout is not None else config.get("WAIT_TIMEOUT", "")
        wait_interval = args.wait_interval if args.wait_interval is not None else config.get("WAIT_INTERVAL", "")
        add_option(command, "wait-timeout", wait_timeout)
        add_option(command, "wait-interval", wait_interval)

    output_format = args.output_format or config.get("OUTPUT_FORMAT", "json")
    if output_format == "json":
        command.append("--json")

    command.append("--no-color")

    return command


def build_utility_command(config, args):
    cli_bin = resolve_cli_binary(args.cli_bin or config.get("HIGGSFIELD_CLI_BIN", "higgsfield"))

    if args.action == "model-list":
        command = [cli_bin, "model", "list", "--json", "--no-color"]
        return command

    if args.action == "job-get":
        if not args.job_id:
            raise ValueError("--job-id 값이 필요합니다.")
        command = [cli_bin, "generate", "get", args.job_id, "--json", "--no-color"]
        return command

    if args.action == "job-wait":
        if not args.job_id:
            raise ValueError("--job-id 값이 필요합니다.")
        command = [cli_bin, "generate", "wait", args.job_id, "--json", "--no-color"]
        return command

    if args.action == "job-list":
        command = [cli_bin, "generate", "list", "--json", "--no-color"]
        return command

    raise ValueError(f"지원하지 않는 액션입니다: {args.action}")


def command_to_safe_string(command):
    safe_parts = []

    for part in command:
        text = str(part)

        if re.search(r"\s", text):
            text = '"' + text.replace('"', '\\"') + '"'

        safe_parts.append(text)

    return " ".join(safe_parts)


def run_command(command, timeout_seconds):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False
    )


def make_parser():
    parser = argparse.ArgumentParser(
        description="Higgsfield CLI를 사용해 이미지 또는 영상을 생성하는 Antigravity 도구"
    )

    parser.add_argument(
        "--action",
        choices=["create", "cost", "model-list", "job-get", "job-wait", "job-list"],
        default="create",
        help="실행할 작업"
    )
    parser.add_argument("--type", choices=["image", "video"], help="생성 타입")
    parser.add_argument("--prompt", help="생성 프롬프트")
    parser.add_argument("--model", help="Higgsfield 모델명")
    parser.add_argument("--aspect-ratio", help="예: 16:9, 1:1, 9:16")
    parser.add_argument("--resolution", help="예: 2k, 1080p")
    parser.add_argument("--duration", type=int, help="영상 길이 초 단위")
    parser.add_argument("--mode", help="영상 모델 모드")
    parser.add_argument("--sound", help="예: on, off")
    parser.add_argument("--start-image", help="영상 생성 시작 이미지 경로")
    parser.add_argument("--wait", action="store_true", help="생성 완료까지 대기")
    parser.add_argument("--no-wait", action="store_true", help="생성 완료 대기 안 함")
    parser.add_argument("--wait-timeout", help="예: 10m")
    parser.add_argument("--wait-interval", help="예: 3s")
    parser.add_argument("--output-format", choices=["json", "plain_text"], help="출력 형식")
    parser.add_argument("--extra", action="append", help="추가 CLI 옵션. 예: --extra quality=high")
    parser.add_argument("--job-id", help="조회하거나 대기할 Higgsfield job id")
    parser.add_argument("--cli-bin", help="higgsfield CLI 실행 파일 경로 또는 이름")
    parser.add_argument("--dry-run", action="store_true", help="실행하지 않고 명령만 출력")

    return parser


def main():
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

        config = load_config()
        parser = make_parser()
        args = parser.parse_args()

        if args.action in {"create", "cost"}:
            command = build_generate_command(config, args)
        else:
            command = build_utility_command(config, args)

        timeout_seconds = int(config.get("PROCESS_TIMEOUT_SECONDS", 900))
        safe_command = command_to_safe_string(command)

        if args.dry_run:
            result = {
                "status": "success",
                "timestamp": now_string(),
                "dry_run": True,
                "command": safe_command,
                "message": "dry-run 모드입니다. Higgsfield CLI 명령을 실행하지 않았습니다."
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        completed = run_command(command, timeout_seconds)
        parsed_stdout = parse_stdout(completed.stdout)
        result_urls = find_urls(completed.stdout + "\n" + completed.stderr)

        if completed.returncode == 0:
            result = {
                "status": "success",
                "timestamp": now_string(),
                "command": safe_command,
                "returncode": completed.returncode,
                "result_urls": result_urls,
                "parsed_stdout": parsed_stdout,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip()
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        result = {
            "status": "error",
            "timestamp": now_string(),
            "command": safe_command,
            "returncode": completed.returncode,
            "message": "Higgsfield CLI 실행 중 오류가 발생했습니다.",
            "hint": "인증 오류라면 `higgsfield auth login`을 다시 실행하세요. 모델 오류라면 `higgsfield model list`로 사용 가능한 모델명을 확인하세요.",
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip()
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(completed.returncode)

    except subprocess.TimeoutExpired as e:
        error_result = {
            "status": "error",
            "timestamp": now_string(),
            "message": f"명령 실행 시간이 초과되었습니다: {str(e)}",
            "hint": "영상 생성은 시간이 오래 걸릴 수 있습니다. PROCESS_TIMEOUT_SECONDS 또는 WAIT_TIMEOUT 값을 늘려보세요."
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

    except Exception as e:
        error_result = {
            "status": "error",
            "timestamp": now_string(),
            "message": str(e),
            "hint": "Higgsfield CLI 설치 여부와 로그인 상태를 확인하세요. 설치: npm install -g @higgsfield/cli, 로그인: higgsfield auth login",
            "debug": {
                "sys.argv": sys.argv,
                "config_keys": list(config.keys()) if 'config' in locals() else None,
                "config_prompt": config.get('PROMPT') if 'config' in locals() else None
            }
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
