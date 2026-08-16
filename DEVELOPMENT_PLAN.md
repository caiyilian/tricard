# 联机斗地主 · 分阶段开发计划

> 目标：一个可联机的网页斗地主游戏。一桌 3 人，座位可以是真人或 AI；AI 出牌由大模型（SenseNova DeepSeek V4 Flash）决策，后端做二次合法性校验，非法时回退到规则 AI 兜底。

## 总原则
1. **服务端权威**：所有牌只在后端生成与校验，前端只渲染，杜绝作弊。
2. **AI 必须有兜底**：大模型永远被规则 AI 兜底，任何情况下游戏不崩。
3. **每阶段可独立验收**：每一阶段结束都有可运行的代码 + 可由我自动化执行的测试，通过后才进入下一阶段。
4. **密钥永不进仓库**：只有 `.env.example`，真实 key 从本地 `.env`（已被 gitignore）读取。

---

## 技术栈与目录规划

```
tricard/
├── backend/            # Python FastAPI 服务
│   ├── app/
│   │   ├── main.py          # FastAPI 入口 + WebSocket 路由
│   │   ├── config.py        # 从 .env 读配置
│   │   ├── rooms.py         # 房间管理
│   │   └── ws.py            # WebSocket 消息协议
│   ├── doudizhu/            # 纯规则引擎（与网络无关，最先生成、单测最全）
│   │   ├── cards.py         # 牌面表示 / 全集 / 编码
│   │   ├── pattern.py       # 牌型识别 + 大小比较
│   │   ├── game.py          # 对局状态机（发牌/叫地主/出牌/胜负）
│   │   ├── ai_basic.py      # 规则 AI（兜底）
│   │   └── ai_llm.py        # LLM 决策层（JSON / 重试 / 回退）
│   ├── scripts/             # 可运行的自动验证脚本
│   ├── tests/               # pytest
│   └── requirements.txt
├── frontend/           # 阶段 6 起创建（Vue3 + Vite）
├── .env.example
├── .gitignore
└── DEVELOPMENT_PLAN.md
```

自动化测试统一用 **pytest**（后端单测 + WebSocket 集成测试），真实对局用 **scripts/ 下的脚本**跑完整模拟，两者结合就是我的"人工+自动"验收手段。

---

## 阶段 0：项目脚手架与健康检查
**工作量：小（纯环境搭建）**

做：
- 建 `backend/` 目录、`requirements.txt`（fastapi, uvicorn, pydantic, websockets, openai, python-dotenv, pytest, pytest-asyncio）
- `app/config.py`：从 `.env` 读 `SENSENOVA_API_KEYS`（逗号分隔）、`.env.example` 模板
- `app/main.py`：仅一个 `/health` 接口
- `.env` 从 `.env.example` 复制，填入本地真实 key（不进 git）

验收标准：
- [ ] `pip install -r backend/requirements.txt` 无报错
- [ ] `uvicorn app.main:app` 可启动，`/health` 返回 200

我的测试：
```
pip install -r backend/requirements.txt
uvicorn app.main:app --port 8000   # 启动后另开终端
curl http://127.0.0.1:8000/health  # 期望 {"status":"ok"}
```

---

## 阶段 1：牌型识别 + 大小比较（核心算法）
**工作量：小~中（纯函数，无 IO）**

做：
- `cards.py`：牌面表示（点数`3..2,A,小王,大王`，四花色），牌型枚举
- `pattern.py`：
  - `parse_play(cards)` → 识别：单张、对子、三张、三带一、三带二、顺子(≥5)、连对(≥3对)、飞机、飞机带单/对、炸弹、王炸、四带二；非法返回 `None`
  - `can_beat(new, last)`：同型比点数、炸弹>普通、王炸最大、点数序 大王>小王>2>A>K>…>3

验收标准：
- [ ] 每种合法牌型至少 1 个识别用例通过
- [ ] 至少 5 种非法组合（如顺子断张、三带翅膀重复、连对断对）被正确拒绝
- [ ] 炸弹/王炸压任意牌型、王炸最大，比较逻辑全部正确

我的测试：
```
pytest backend/tests/test_pattern.py -v
```
测试数据用写死牌例（不随机）。

---

## 阶段 2：对局状态机（发牌 / 叫地主 / 出牌 / 胜负）
**工作量：中（状态切分清晰）**

做：
- `game.py`：`Game` 类
  - 洗牌发牌（17+17+3 底牌）
  - 叫地主流程（先做简单版：随机/固定逻辑，阶段 5 再接入真人选择）
  - 出牌轮转：`can_play(player, cards, last)` 校验牌在手、牌型合法、能压上家
  - pass / 一轮结束清空、炸弹翻倍计分、任意一人出完即终局
- `scripts/simulate_game.py`：用先后手策略（如总是出最小合法牌）自动跑完整一局，打印逐步记录

验收标准：
- [ ] `Game` 从发牌到终局全程状态正确（出牌者轮转、pass 规则、胜负判定）
- [ ] 任何非法出牌都被 `can_play` 拒绝
- [ ] `simulate_game.py` 可完成整局且每步出牌都合法

我的测试：
```
pytest backend/tests/test_game.py -v
python backend/scripts/simulate_game.py   # 应打印完整对局并正常结束
```

---

## 阶段 3：规则 AI（所有 AI 的兜底）
**工作量：小（贪心策略）**

做：
- `ai_basic.py`：
  - 首出策略：拆解手牌，优先出单张/最小对子等
  - 应牌策略：从手牌中找"最小能压上家"的组合；压不住则 pass
  - 记牌：统计已出牌，推断下家剩牌类型（简单版）

验收标准：
- [ ] 任意局面下 AI 输出都通过 `Game.can_play` 校验（合法性 100%）
- [ ] AI vs AI 对局 100 盘全部正常结束、无死循环、无异常

我的测试：
```
pytest backend/tests/test_ai_basic.py -v
python backend/scripts/auto_battle.py 100   # 100 盘自动对局汇总统计
```

---

## 阶段 4：LLM 决策层（消耗额度的核心）
**工作量：小~中（网络 + 校验 + 回退）**

做：
- `config.py` 读取 7 个 key，写 `SimpleKeyPicker` 轮换调度（均匀消耗额度）
- `ai_llm.py`：
  1. 组装上下文 prompt：手牌 / 上家出牌 / 身份 / 剩余牌数
  2. 调 SenseNova（openai 兼容，`response_format=json_object`），要求输出 `{"action":"play|pass","cards":[...]}`
  3. 解析并二次校验（复用 `pattern.py` + `Game.can_play`）
  4. 非法 → 重试 1 次；仍失败 → 回退 `ai_basic` 兜底
- `scripts/hand_test.py`：手工摆一个局面，真实调用一次 LLM，打印决策+校验结果（消耗极小，用于压测额度是否正常）

验收标准：
- [ ] 用 **mock**（不真实调用）模拟 LLM 返回非法牌 → 触发重试/回退，不崩溃
- [ ] 7 个 key 轮换顺序正确（日志可见换 key）
- [ ] 真实调用 `hand_test.py` 1 次能返回合法 JSON 决策

我的测试：
```
pytest backend/tests/test_ai_llm.py -v     # mock LLM，不耗额度
python backend/scripts/hand_test.py        # 真实调用 1 次，人工看输出
```

---

## 阶段 5：FastAPI + WebSocket 联机房间
**工作量：中（涉及协议与并发）**

做：
- `rooms.py`：6 位房号、创建/加入/退出、座位占用（真人抢占时 AI 让位）
- `ws.py` WebSocket 协议（明确消息格式，见下）
- 广播：准备、叫地主选择、出牌、pass、牌局结束、房间人数变化
- 座位规则：1~3 个真人，空位由 AI（先规则 AI，阶段 4 完成则用 LLM AI）自动补位；名额可配置
- 断线：掉线保留座位 30 秒，重连同步全量状态
- `scripts/ws_clients.py`：3 个模拟客户端自动连接打完整一局（验收核心）

验收标准：
- [ ] 3 个 WebSocket 客户端能加入同一房间并完整打完一局
- [ ] 消息协议在 1 个真人 + 2 AI 场景下正确广播
- [ ] 断线重连续传正常
- [ ] 不同房间相互隔离

我的测试：
```
pytest backend/tests/test_ws_game.py -v        # asyncio 多客户端集成测试
python backend/scripts/ws_clients.py 123456    # 手动跑 3 个模拟客户端打一局
```

---

## 阶段 6：前端 Vite + Vue3
**工作量：中（界面 + 交互 + 协议对接）**

做：
- 房间页：输入/创建房号、座位显示（真人/AI 标签）
- 游戏页：手牌渲染（CSS 画扑克牌）、出牌区、上家/下家手牌数量、回合提示、叫地主按钮、倒计时
- 出牌动画：轮到自己 → 选牌 → 出牌/不出
- WebSocket 对接后端协议，状态全由服务端广播驱动
- 支持「单机模式」：1 真人 + 2 AI（本地连自己房间，等同 1 人房）

验收标准：
- [ ] `npm run dev` 启动无报错
- [ ] 本地起后端后，一个浏览器窗口（1 真人 + 2 AI）能完整打完一局
- [ ] 两个浏览器窗口（2 真人 + 1 AI）联机对战正常
- [ ] 出牌/不出按钮与回合状态正确

我的测试：
```
cd frontend && npm install && npm run dev
# 后端已启动时，浏览器打开打局；自动化用 Playwright 冒烟：
pytest backend/tests/test_e2e_smoke.py -v   # 仅验证页面加载 + 首屏渲染（可选阶段）
```

---

## 阶段 7：体验完善与部署说明（可选增强）
**工作量：每项都小，按需选择**

做：
- 效果优化：动画细化、音效、「思考中」AI 加载提示、KO 结算动画
- 功能增强：大厅房间列表、战绩统计、聊天、旁观模式、残局挑战（用多余额度批量生成题库）
- 部署：`Dockerfile` + `docker-compose.yml`（后端 + 静态前端 + 可选 nginx），一键起

验收标准：
- [ ] 每项功能有独立脚本或人工清单可验收
- [ ] `docker compose up` 后一个命令起整套，浏览器可玩

我的测试：
```
docker compose up -d
curl http://localhost:8000/health && 浏览器 http://localhost:5173 手测
```

---

## 全局测试清单（每阶段必须全绿再往下走）

| 阶段 | 命令 | 期望 |
|------|------|------|
| 0 | `curl /health` | 200 |
| 1 | `pytest test_pattern.py` | 全过 |
| 2 | `pytest test_game.py` + simulate | 全过 + 整局完成 |
| 3 | `pytest test_ai_basic.py` + auto_battle | 全过 + 100盘无异常 |
| 4 | `pytest test_ai_llm.py` + hand_test | 全过 + 真实调用合法 |
| 5 | `pytest test_ws_game.py` + ws_clients | 全过 + 3客户端整局 |
| 6 | `npm run dev` + 浏览器 | 可完整对战 |
| 7 | `docker compose up` | 一键可玩 |

## 进度记录

- [ ] 阶段 0：脚手架与健康检查
- [ ] 阶段 1：牌型识别与比较
- [ ] 阶段 2：对局状态机
- [ ] 阶段 3：规则 AI
- [ ] 阶段 4：LLM 决策层
- [ ] 阶段 5：WebSocket 联机
- [ ] 阶段 6：前端界面
- [ ] 阶段 7：体验完善与部署