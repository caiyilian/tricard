# tricard — 局域网联机斗地主

一个**局域网（LAN）可联机**的网页斗地主：一桌 3 人，座位可以是真人或 AI；
AI 出牌由大模型（senseNova `sensenova-6.8-flash-lite`）决策，后端做二次合法性校验，非法时自动回退规则 AI 兜底。
带账号系统、欢乐豆结算、排行榜、AI 嘲讽/夸奖（弹幕人格）——完整复刻市面斗地主体验。

![tech](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)
![Vue](https://img.shields.io/badge/Vue3-4FC08D?logo=vuedotjs)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite)
![Lang](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)

---

## 功能特性

- **三种 AI 自由混搭一桌**（座位独立配置）：`basic` 规则 AI / `douzero` 强化学习 AI / `llm` 大模型 AI
  - LLM 定位"拟人玩家"：会失误、会贪、像真人；DouZero 定位"职业选手"（零额度，离线推理）
- **LLM 决策层**：每回合构建"开卷考"局面快照（手牌/完整出牌记录/记牌表/身份），强制 JSON 输出，服务端二次校验
  - 7 个 API 账号**每次调用均匀轮询**，适配 5 小时滚动窗口；429/余额受限自动跳过
  - `reasoning_effort="none"` 关闭思考模式，单次调用 token 降 65 倍
- **AI 评论系统**：桌上独立的 LLM 观察者决定"谁说话"，任何 AI 座位（含 DouZero/规则 AI）都能被分配嘲讽/夸奖台词
  - 有因果不刷屏：规则预筛"坑队友/神操作"局面 + 羞耻值累计 + 冷却；三种模式（`rules_only`/`hybrid`/`llm_judge`）
- **欢乐豆 + 账号**：注册登录、昵称/头像上传、胜场/败场/胜率、欢乐豆可为负
  - 结算复用市面规则：炸弹/王炸翻倍、春天 ×2、地主 ±2 倍
  - 排行榜三榜：欢乐豆 / 胜场 / 胜率（胜率要求至少 5 场）
- **局域网房间**：大厅直接看到所有房间（人数/状态/底分）点进即玩；房号搜索精确加入；全就绪房主开局；断线重连
- **出牌限时**：默认 30s/手（可配），领出超时自动出最小合法牌、否则自动"过"，永不卡局

## 技术栈与复用

| 用途 | 选型 |
|------|------|
| 后端 | FastAPI + python-socketio + SQLAlchemy 2.x（SQLite 本机库） |
| 牌型引擎 | [onestraw/doudizhu](https://github.com/onestraw/doudizhu)（MIT，37 牌型 O(1) 判断） |
| 强化学习 AI | [kwai/DouZero](https://github.com/kwai/DouZero)（Apache-2.0，预训练权重本地推理） |
| 大模型 | senseNova 平台 `sensenova-6.8-flash-lite`（OpenAI 兼容，`https://token.sensenova.cn/v1`） |
| 前端 | Vue 3 + Vite（`frontend/`，阶段 6 起） |

## 目录结构

```
tricard/
├── backend/
│   ├── app/            # FastAPI：auth/users/beans/ranking/rooms/socketio/db
│   ├── doudizhu/       # 游戏引擎 + AI（ai_basic / ai_llm / ai_douzero / commentary）
│   ├── scripts/        # 自动验证脚本（llm_api_test / auto_battle / seed_ai ...）
│   └── tests/          # pytest
├── frontend/           # Vue3 前端（阶段 6 起）
├── third_party/        # 克隆的开源项目（不入库）
├── docs_local/         # 本地文档/离线资料（不入库）
└── DEVELOPMENT_PLAN.md # 分阶段开发计划（含验收与测试）
```

## 快速开始（当前进度：阶段 0~2.5 设计完成，代码开发中）

### 1. 环境

- Python 3.11（用 [uv](https://docs.astral.sh/uv/) 管理）

```powershell
uv venv .venv --python 3.11
uv pip install -r backend/requirements.txt
```

- torch：需 CUDA wheel（DouZero 推理用）。若 7890 代理下 `pip install torch` 超时，可本地安装 whl：

```powershell
uv pip install "C:\path\to\torch-2.5.1+cu124-cp311-cp311-win_amd64.whl"
```

建议版本：`Python 3.11` + `torch 2.5.1+cu124`（2.5.1 是最后一个默认 `weights_only=False` 的版本，可直接加载 DouZero 老权重）。

### 2. 配置文件

复制 `.env.example` 为 `.env`，填入 7 个 senseNova API key（逗号分隔）。

> 密钥文件（`sensenova_apikey.txt`、`github-token.txt`、`.env`）与离线资料均在 `.gitignore` 中，不会上传。

### 3. 预训练权重（DouZero）

Apache-2.0 官方权重，结构如下，放到 `backend/models/`（不入库）：

```
backend/models/
├── douzero_ADP/{landlord,landlord_up,landlord_down}.ckpt
├── douzero_WP/{landlord,landlord_up,landlord_down}.ckpt
└── sl/{landlord,landlord_up,landlord_down}.ckpt
```

下载源见 [DouZero README](https://github.com/kwai/DouZero)：Google Drive / 百度网盘（提取码 `4624`）。

### 4. 初始化数据库与 AI 账号

```powershell
uv run python backend/scripts/seed_ai.py --ensure
```

创建 `backend/data/doudizhu.db`，并写入 N 个带欢乐豆的 AI 账号（幂等，可重复执行）。

### 5. 启动后端

```powershell
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

局域网其他设备访问 `http://<本机IP>:8000`（前端完成后同一地址）。

## 验证与诊断

```powershell
# LLM 层健康检查（游戏出问题先跑这个，排除是否 LLM 故障）
uv run python backend/scripts/llm_api_test.py

# DouZero 冒烟 + 完整对战
uv run python backend/scripts/douzero_smoke.py
uv run python backend/scripts/douzero_env_test.py

# 自动对战（任意混排，如 1 LLM + 2 DouZero）
uv run python backend/scripts/auto_battle.py 20 --mix llm,douzero,douzero
```

## 开发计划

完整分阶段计划、验收标准、自测命令见 [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md)。

| 阶段 | 内容 | 状态 |
|------|------|------|
| 0 | 脚手架 + /health | 设计中（环境已就绪） |
| 1 | 复用牌型引擎 + 游戏状态机 | 待开发 |
| 2 | 规则 AI 兜底 | 待开发 |
| 2.5 | 账号系统 + 欢乐豆 + 排行榜 | 待开发 |
| 3 | LLM 决策层（7 key 轮询） | 待开发 |
| 4 | DouZero 强 AI | 引擎验证通过，待接入 |
| 4.5 | AI 评论系统 | 待开发 |
| 5 | SocketIO 联机房间 + 局域网发现 | 待开发 |
| 6 | Vue3 前端 | 待开发 |
| 7 | 体验完善 + 一键启动 | 待开发 |

## 许可证说明

- 本项目代码部分计划采用 MIT 协议
- 依赖的开源项目按其各自许可证（MIT / Apache-2.0）使用，详见[复用清单](#技术栈与复用)