# 🎬 Higgsfield 이미지·영상 생성 도구

Higgsfield CLI를 사용해 텍스트 프롬프트 기반 이미지 또는 영상을 생성하고, 실행 결과를 JSON 형태로 출력하는 도구입니다. 에이전트가 사용자의 요청을 받아 Higgsfield 모델로 이미지, 영상, 제품컷, 시네마틱 장면, 광고용 비주얼 등을 생성해야 할 때 사용하세요.

이 도구는 직접 API Key를 코드에 저장하지 않고, 로컬 환경에 설치된 `higgsfield` CLI와 `higgsfield auth login`으로 완료된 인증 세션을 사용합니다.

## 사용 시점

- 텍스트 프롬프트로 이미지를 생성해야 할 때
- 텍스트 프롬프트로 영상을 생성해야 할 때
- 시작 이미지나 참조 이미지를 기반으로 영상을 생성해야 할 때
- 생성 결과 URL, 작업 상태, CLI 출력값을 에이전트가 읽기 쉬운 JSON으로 받고 싶을 때
- Higgsfield 모델을 Antigravity 에이전트 워크플로우에 연결하고 싶을 때

## 입력 / 설정

이 도구는 같은 폴더의 `higgsfield_media_generator.json` 파일에서 기본 설정값을 읽어옵니다.

주요 설정값은 다음과 같습니다.

- `GENERATION_TYPE`: `"image"` 또는 `"video"`
- `PROMPT`: 생성할 이미지 또는 영상에 대한 설명
- `IMAGE_MODEL`: 이미지 생성에 사용할 Higgsfield 모델
- `VIDEO_MODEL`: 영상 생성에 사용할 Higgsfield 모델
- `ASPECT_RATIO`: 예: `"16:9"`, `"1:1"`, `"9:16"`
- `RESOLUTION`: 예: `"2k"`, `"1080p"`
- `DURATION`: 영상 길이 초 단위
- `START_IMAGE`: 영상 생성에 사용할 시작 이미지 경로
- `WAIT_FOR_RESULT`: 결과가 나올 때까지 대기할지 여부
- `EXTRA_ARGS`: Higgsfield CLI에 추가로 넘길 옵션

파이썬 실행 시 CLI 인자로 설정값을 덮어쓸 수 있습니다.

예시:

```bash
python higgsfield_media_generator.py --type image --prompt "a cinematic product photo of a futuristic sneaker"
```

```bash
python higgsfield_media_generator.py --type video --prompt "slow camera push through a neon city street" --start-image ./first.png --duration 5
```

## 사전 준비

Higgsfield CLI가 설치되어 있어야 합니다.

```bash
npm install -g @higgsfield/cli
```

최초 1회 로그인 인증이 필요합니다.

```bash
higgsfield auth login
```

## 출력

기본 출력은 JSON입니다.

성공 시 예시:

```json
{
  "status": "success",
  "timestamp": "2026-05-21 10:30:00",
  "command": "higgsfield generate create nano_banana_2 ...",
  "returncode": 0,
  "result_urls": ["https://..."],
  "stdout": "...",
  "stderr": ""
}
```

실패 시 예시:

```json
{
  "status": "error",
  "timestamp": "2026-05-21 10:30:00",
  "message": "Higgsfield CLI를 찾을 수 없습니다.",
  "hint": "npm install -g @higgsfield/cli 후 higgsfield auth login을 실행하세요."
}
```

## 주의사항

- 이 도구는 Higgsfield CLI 인증 세션을 사용하므로 먼저 `higgsfield auth login`이 완료되어 있어야 합니다.
- 생성 작업은 Higgsfield 계정 크레딧을 사용할 수 있습니다.
- 인증 토큰, 계정 정보, 결제 정보, 민감 정보는 출력하지 않습니다.
- 타인의 초상, 저작권이 있는 캐릭터, 브랜드 자산, 민감한 개인 이미지 등을 사용할 때는 반드시 권한을 확인해야 합니다.
- 불법적, 기만적, 유해한 콘텐츠 생성을 목적으로 사용하지 않습니다.
- json 파일의 `_do`, `_dont` 지침을 반드시 따른다고 가정하고 설계합니다.
