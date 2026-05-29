# cli-voicebox

[Voicebox](https://voicebox.sh/) 本地语音合成服务的命令行工具：健康检查、列出音色配置、文本转语音、下载音频与查询历史。配置通过 JSON 文件加载。

API 文档：[Voicebox API Reference](https://docs.voicebox.sh/api-reference)

## 前置条件

1. 安装并启动 [Voicebox](https://voicebox.sh/) 桌面应用
2. 默认 REST 地址：`http://127.0.0.1:17493`（可在应用设置中查看）
3. 本地 OpenAPI：`http://127.0.0.1:17493/docs`

## 安装

### 从 GitHub 安装

目标机器需 **Python ≥ 3.11**。

```bash
pip install git+https://github.com/AICodeFactory/cli-voicebox.git
voicebox-cli --help
```

### 克隆后本地开发安装

```bash
git clone https://github.com/AICodeFactory/cli-voicebox.git
cd cli-voicebox
pip install -e .
# 或: uv sync && uv run voicebox-cli --help
```

## 配置

**不依赖当前工作目录。** 执行 `--help` 或首次调用子命令时，若配置不存在会自动创建用户配置目录：

```bash
voicebox-cli init
voicebox-cli --help   # 显示本机 config.json 路径
```

覆盖默认路径：

```bash
voicebox-cli -c /path/to/config.json profiles
export VOICEBOX_CLI_CONFIG=/path/to/config.json
export VOICEBOX_BASE_URL=http://127.0.0.1:17493
```

`config.json` 字段：

| 字段 | 说明 |
|------|------|
| `voicebox_url` | Voicebox 服务地址，默认 `http://127.0.0.1:17493` |
| `timeout_seconds` | HTTP 超时（生成可能较慢，默认 600） |

环境变量：`VOICEBOX_BASE_URL`、`VOICEBOX_TIMEOUT`、`VOICEBOX_CLI_CONFIG`。

## 命令

### `health` — 健康检查

对应 [GET /health](https://docs.voicebox.sh/api-reference/general/health__get) 与可选 [GET /](https://docs.voicebox.sh/api-reference/general/root__get)：

```bash
voicebox-cli health
voicebox-cli health --include-root
```

### `profiles` — 列出音色

```bash
voicebox-cli profiles
```

### `generate` — 文本转语音

对应 [POST /generate](https://docs.voicebox.sh/developer/tts-generation)：

```bash
# 先获取 profile_id
voicebox-cli profiles

voicebox-cli generate \
  -t "Hello world" \
  --profile-id "<uuid>" \
  -o hello.wav
```

从 JSON 文件传入完整请求体：

```bash
voicebox-cli generate --body-file request.json -o out.wav
```

可选参数：`--language`、`--engine`、`--seed`、`--model-size`、`--instruct`、`--max-chunk-chars`。

### `audio` — 按 generation id 下载音频

```bash
voicebox-cli audio --generation-id "<uuid>" --audio-out out.wav
```

### `history` — 生成历史

```bash
voicebox-cli history --limit 20
```

### `models` — 模型状态

```bash
voicebox-cli models
```

### 输出格式

默认 JSON。人类可读：

```bash
voicebox-cli profiles --format text
```

### 退出码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | 失败（配置错误、服务未启动、API 错误等） |

## 与 cli-comfyui 的关系

本仓库结构与 [cli-comfyui](https://github.com/AICodeFactory/cli-comfyui) 一致：`init`、JSON 配置目录、`httpx` 调用远程服务、stdout JSON 输出，便于脚本与 Agent 集成。

## 参考

- [Voicebox 官网](https://voicebox.sh/)
- [TTS Generation 开发文档](https://docs.voicebox.sh/developer/tts-generation)
- [Voice Profiles API](https://docs.voicebox.sh/developer/voice-profiles)
