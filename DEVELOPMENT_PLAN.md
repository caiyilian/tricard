# 联机斗地主 · 分阶段开发计划（v2）

> 目标：一个**可联机的网页斗地主游戏**，主打**局域网（LAN）联机**。一桌 3 人，座位可以是真人或 AI；AI 出牌由大模型（SenseNova DeepSeek V4 Flash）决策，后端做二次合法性校验，非法时回退到规则 AI 兜底。

## 三项开发信条
1. **不追求轻量化**：怎么好开发、好维护怎么来，不为了"轻"去用难用的库。前端 React 或 Vue 均可，本项目选 **Vue 3 + Vite**（生态熟、配 FastAPI 后端直接）。
2. **减少重复造轮子**：能直接用的开源项目/库就用，见下方「复用清单」。
3. **目标只是局域网联机**：不做公网部署、不要 HTTPS/账号体系，一个房号 + 局域网 IP 即可开打，部署只求"本地一条命令起来"。

## 复用清单（已核实许可证）
> 原则：只复用 **MIT / Apache-2.0** 等项目，无许可证（如 svzdev/doudizhu、rlcard-showdown）只当参考、不搬代码。

| 用途 | 项目 | 许可 | 说明 |
|------|------|------|------|
| 牌型引擎（识别/比较/提示/发牌） | [onestraw/doudizhu](https://github.com/onestraw/doudizhu)（PyPI 包名 `doudizhu`） | MIT | 枚举 37 种牌型 O(1) 判断，含 `check_card_type` / `cards_greater` / `list_greater_cards`，省掉最易错的核心算法 |
| 强 AI 对手（离线「高手」档） | [kwai/DouZero](https://github.com/kwai/DouZero)（PyPI 包名 `douzero`） | Apache-2.0 | ICML2021 强化学习斗地主 AI，Win 下 CPU 可推理；提供预训练模型，作为可选高难度 AI，不消耗 API 额度 |
| 实时通信 | [`python-socketio`](https://python-socketio.readthedocs.io/) + [`socket.io-client`](https://socket.io/) | MIT | 自带房间(room)、心跳、**断线自动重连**与补齐事件——正好覆盖「断线重连」验收点，避免手搓 WebSocket 协议 |
| 前端框架 | Vue 3 + Vite + vue-router | MIT | 界面渲染，牌面用 CSS/SVG 绘制 |
| 参考实现（不搬代码） | [svzdev/doudizhu](https://github.com/svzdev/doudizhu)、[datamllab/rlcard-showdown](https://github.com/datamllab/rlcard-showdown) | 无许可证，仅参考 | 借鉴 UI 布局、牌桌交互、游戏流程设计思路 |

**需要自研的部分（无现成、且是本项目核心）**：对局流程状态机（叫地主/轮转/胜负）、LLM 决策层（7 key 轮换 + 校验 + 回退）、房间管理、简易规则 AI 兜底（约百行贪心）。

---

## 技术栈与目录规划

```
tricard/
├── backend/            # Python FastAPI 服务
│   ├── app/
│   │   ├── main.py          # FastAPI 入口（HTTP 静态 + SocketIO 路由）
│   │   ├── config.py        # 从 .env 读配置
│   │   ├── db.py            # SQLAlchemy engine + session
│   │   ├── models.py        # User / MatchRecord（欢乐豆、战绩落库）
│   │   ├── security.py      # pbkdf2 密码哈希 + token
│   │   ├── auth.py          # 注册/登录路由
│   │   ├── beans.py         # 欢乐豆结算（纯函数，好单测）
│   │   ├── rooms.py         # 房间管理（房号/座位/AI补位）
│   │   └── socketio_routes.py # SocketIO 事件处理
│   ├── doudizhu/            # 业务逻辑（牌规则复用 doudizhu 库，其上再加游戏流程）
│   │   ├── game.py          # 对局状态机（叫地主/出牌轮转/胜负）★自研
│   │   ├── ai_basic.py      # 规则 AI 兜底（~100 行贪心）★自研
│   │   ├── ai_llm.py        # LLM 决策层（JSON/重试/回退）★自研
│   │   ├── ai_douzero.py    # DouZero 强 AI（离线价值网络）★封装
│   │   ├── commentary/      # AI 评论系统（嘲讽/夸奖，见「评论系统设计」）
│   │   │   ├── detector.py      # 局面探测器（确定性规则，非随机）
│   │   │   ├── salience.py      # 显著度评估 + 频控（羞耻值累计）
│   │   │   ├── phrase_bank.py   # 零额度短语库
│   │   │   ├── llm_commentator.py # 独立评论 LLM（判断+指定 speaker+措辞）
│   │   │   └── commentator.py   # 编排 + 广播
│   │   └── key_picker.py    # 7 个 key 轮换调度 ★自研
│   ├── scripts/             # 可运行的自动验证脚本
│   │   └── seed_ai.py       # 建表 + 建 AI 账号 + 回补豆子
│   ├── tests/               # pytest
│   └── requirements.txt
├── frontend/           # 阶段 6 起创建（Vue3 + Vite）
├── .env.example
├── .gitignore
└── DEVELOPMENT_PLAN.md
```

### AI 难度设计（传统 AI 与 LLM 并存，两种定位不同）
| 档位 | 实现 | 定位 | 手感 |
|------|------|------|------|
| `basic` | 规则 AI（贪心兜底） | 新手 | 稳定可预测，适合入门 |
| `douzero` | DouZero 预训练价值网络（离线、零额度） | 职业选手 | 决策合理、整体强，严肃竞技 |
| `llm` | 大模型 + 后端二次校验（非法则回退兜底） | 拟人玩家 | **会失误、会贪、偶尔乱出，很像真人**，自带节目效果 |

设计原则：
1. **LLM 的价值不在"赢"，而在"像人"**——它出差错正是趣味所在，不追求胜过 DouZero。
2. 座位难度可独立配置：比如"1 真人 + 1 个 DouZero + 1 个 LLM"或 3 个真人，自由组合。
3. DouZero 负责严肃游戏（零额度），LLM 负责拟人氛围，两端定位不同、不浪费额度。

### AI 评论系统设计（嘲讽 / 夸奖 / 弹幕人格）

**评价时每次出牌 AI 的解耦 —— 先回答你上面的问题：**
> 评论能力**不属于出牌 AI**，桌上有一个**独立的 LLM 观察者（Commentator，每桌一个）**负责"判断 + 措辞 + 指定发言人"。
> 所以的 AI 座位（不管是 LLM 还是 DouZero / 规则 AI）都**可以开口**，由 Commentator 指定谁来嘲讽/夸奖。
> 每回合都会快速判断一次是否值得说话（省 token 的预筛 + LLM 判断，见下），单桌混排和任意 AI 类型组合均支持。

**核心理念**
- **有因果、不是随机刷屏**：先由**规则检测器**预筛出"确定的坑/亮点"事件，再由 Commentator 判断值不值得说、谁来说、怎么说；不靠随机。
- **团队关系感知**：Commentator 知道每个 AI 座位与目标的关系（队友 / 对手），口吻不同——是队友就"损"（"你是不是在演我？"），是对手就嘲讽。
- **评论与出牌解耦**：`commentator` 是独立 LLM 调用流，**不耗出牌 LLM 的调用次数**；DouZero/规则 AI 座位照常被分配台词。
- **连续坑 = 连续被嘲**：靠**羞耻值累计**与**冷却**控制频率，一次失误不会立刻挨怼，越坑台词越密。

**架构**
```
commentary/
├── detector.py       # 规则预筛：消费事件流，输出 (archetype, 目标座位, 显著度)（零额度）
├── salience.py       # 显著度评估 + 频控（冷却/羞耻累计/每局上限）
├── commentator.py    # 每桌一个：编排 预筛 → LLM 判断 → 措辞 → 广播
├── llm_commentator.py # Commentator LLM：判断是否值得说 + 指定 speaker + 生成措辞
└── phrase_bank.py     # 回退措辞库（零额度，任何一步失败兜底）
```
Commentator 每回合输入（精简局面快照）：本回合谁出了什么/过了、各方剩牌变化、最近 2~3 手、各 AI 座位人格、与目标的关系；输出 JSON：
```
{"should_comment": true, "speaker": "农民-1", "tone": "savage", "text": "……"}
```

**触发源 = 游戏事件流**：`play / pass / bomb / round_end / game_end`。即时检测 move 级事件；每轮结束做一次"整轮复盘"。评论只在**天然停顿处**输出（回合结算/整轮结束/胜负点），不打断交互。

**判断模式（config：`commentator.mode`）**
| 模式 | 触发节流 | 额度 | 说明 |
|------|------|------|------|
| `rules_only`（默认） | 规则预筛显著度达标才触发，措辞走短语库 | 0 | 最省，AI 完全不说话之外的兜底 |
| `hybrid` | 规则预筛达标 → LLM 判断+措辞，miss 则短语库 | 低 | 有节制的 LLM 节目效果 |
| `llm_judge` | **每回合都问 Commentator**（低 token 快速判断） | 高 | 最拟人、最灵动，测试/展示用 |

**检测器清单（确定性规则）** —— 非随机，构造具体局面即断言触发：
| ID | 名称 | 示例规则（命中即产生"显著度"） |
|----|------|----|
| `keng_stepping` | 踩队友 | 农民打出的牌压过队友即将收尾的一手，随后被地主压死并加速地主出完 |
| `keng_boost` | 帮倒忙 | 地主剩牌 ≤3 且己方能压却过一手（直接让地主清空） |
| `keng_no_send` | 不送牌 | 队友剩 1 张，自己起手却丢对子/大牌，不给队友走单的机会 |
| `keng_friendly_fire` | 误伤 | 两农民互相炸弹消耗 |
| `keng_blow` | 送葬 | 大优势（己方低剩牌）因一手失误被翻盘 |
| `bright_bomb` | 神炸 | 炸弹时机精准，炸后队友获得掌控并获胜 |
| `bright_send` | 送跑 | 给剩 1 张的队友送单，队友光速获胜 |
| `bright_comeback` | 绝地 | 劣势局完成反超获胜 |
（地主视角自动映射同构变体：神走位 / 被两农民反杀 等）

**频控（不刷屏）**
- **显著度** = 规则强度 × 累计羞耻/荣誉系数，达标才触发，触发后该座位系数归零。
- 每座位冷却 N 回合；全局每轮最多 M 条；每局每座位最多 K 条（N/M/K 做成配置）。
- 评价对象包括真人玩家 —— 你说得对：真人跟 AI 一队坑了它，它也会损你。

**措辞生成（Commentator 集成，双通道）**
1. `hybrid`/`llm_judge` 模式：Commentator 判断"值得说"后，直接生成措辞并指定 `speaker`（任意 AI 座位，含 DouZero/规则 AI）；prompt 含 archetype、speaker 与目标关系、该轮牌序、目标剩牌变化、speaker 人格；强制 `json_object` 输出 1~2 句话。
2. LLM 失败/超时 → 回退 `phrase_bank`（按 archetype+力度+speaker 人格填名），**永不阻塞牌局**。
3. 额度控制：`hybrid` 下每局 Commentator 调用默认 ≤2 条判断；`rules_only` 零额度；出牌 LLM 的调用与评论互不占用。

**人格开关（每座位可配，作用于被指派的台词口感）**：`off`（该座位不评论）/ `kind`（温和多夸）/ `savage`（毒舌多嘲）/ `chatterbox`（话多）。前端以聊天气泡 + 弹幕形式展示。

**与聊天共存**：真人聊天走 `chat` 事件；AI 评论走 `comment` 事件，前端不同样式，不冲突。

自动化测试统一用 **pytest**（单测 + SocketIO 多客户端集成测试），真实对局用 `scripts/` 脚本模拟，负责我的"自测验收"。

---

## 阶段 0：项目脚手架与健康检查
**工作量：小（环境搭建）**

做：
- `backend/` 目录、`requirements.txt`：`fastapi`、`uvicorn`、`python-socketio`、`python-dotenv`、`doudizhu`、`openai`、`pytest`、`pytest-asyncio`
- `app/config.py`：从 `.env` 读 `SENSENOVA_API_KEYS`（逗号分隔 7 个）；提供 `.env.example`
- `app/main.py`：`/health` + 挂一个 SocketIO（空路由占位）
- `.env` 由 `.env.example` 复制后填充本地真实 key（不入 git）

验收标准：
- [ ] `pip install -r backend/requirements.txt` 无报错（含 `doudizhu` 库可 import）
- [ ] `/health` 返回 200，SocketIO `/socket.io/` 握手成功

我的测试：
```
pip install -r backend/requirements.txt
uvicorn app.main:app --port 8000   # 另开终端：
curl http://127.0.0.1:8000/health  # 期望 {"status":"ok"}
# socketio 握手：python backend/scripts/smoke_socketio.py
```

---

## 阶段 1：复用牌型引擎 + 游戏状态机
**工作量：小~中（不写底层算法，写流程）**

做：
- 直接用 `doudizhu` 库做牌型识别/大小比较/提示（写完 `dou_dz_adapter.py` 薄封装：统一出入参，方便测试替身）
- 自研 `game.py` 对局状态机：
  - 发牌（17+17+3 底牌）、叫地主（先简单：随机/固定）
  - 出牌轮转、`can_play`（牌在手 + 牌型合法 + 能压上家）、pass、一轮清空
  - 胜负判定；输出对局记录

验收标准：
- [ ] 库的 37 牌型全部走通一遍集成测试样板（`list_greater_cards` 提示与比较正确）
- [ ] `Game` 从发牌到终局状态正确，非法出牌 100% 被拒
- [ ] `scripts/simulate_game.py` 能完整跑完一局，每步出牌均合法

我的测试：
```
pytest backend/tests/test_game.py -v
python backend/scripts/simulate_game.py   # 应打印完整对局并正常结束
```

---

## 阶段 2：规则 AI 兜底
**工作量：小（贪心）**

做：
- `ai_basic.py`：首出拆牌策略 + 应牌"最小能压"策略 + 压不住就 pass
- 复用 `doudizhu` 的 `list_greater_cards` 获得候选，降低实现量

验收标准：
- [ ] 任意局面 AI 出牌都通过 `Game.can_play`（合法性 100%）
- [ ] AI vs AI 100 盘全部正常结束、无死循环、无异常

我的测试：
```
pytest backend/tests/test_ai_basic.py -v
python backend/scripts/auto_battle.py 100
```

---

## 阶段 2.5：账号系统 + 欢乐豆（本地服务器数据库）
**工作量：中（DB + 鉴权 + 结算公式）**

### 设计

**存储**：本机 SQLite（`backend/data/doudizhu.db`，已 gitignore），用 **SQLAlchemy 2.x ORM**（开箱即用、配 FastAPI 顺手）。局域网单服务器并发低，SQLite 完全够。

**账号**
- `User`：`id / username（唯一）/ password_hash（pbkdf2+盐，不存明文）/ nickname / is_ai / joy_beans / 战绩字段`
- HTTP 账号接口：注册、登录（返回 token，后续 SocketIO connect 携带做信令鉴权）、改昵称
- **AI 账号预设**：`scripts/seed_ai.py` 启动时（或单独命令）创建 N 个 AI 账号（有名字、有初始欢乐豆，如每人 10 万），供真人开房选用；输光豆子的 AI 由脚本一键回补

**欢乐豆（结算规则与服务端权威）**
```
底分 base_bet：开房时可选（如 200 / 1000 / 5000 场）
倍数 multiplier = 1
    × 叫分系数（叫1/2/3，简化版先固定 1×）
    × 2^炸弹数（含王炸，每炸翻一倍）          ← 用户点名要的"炸弹翻倍"
    × 2（春天：地主一手出完 / 农民完胜地主未出过牌）
结算：
    地主胜：+2 × base_bet × multiplier（两农民各扣 base_bet × multiplier）
    地主负：-2 × base_bet × multiplier（两农民各得 base_bet × multiplier）
```
- 结算在 `game_over` 由**服务端权威**计算并写 DB、广播结算面板（含每项翻倍明细），前端只展示
- **房门票**：欢乐豆 < `base_bet` 的账号不能入房（市面同款"快乐豆不足"拦截）
- 输光/不足由前端提示充不上（局域网可让房主一键给 AI/所有人回补额度，或个人单机随便造场景）

### 做
- `requirements.txt` 加 `sqlalchemy`
- `app/db.py`（engine + session）、`app/models.py`（User / MatchRecord）、`app/security.py`（pbkdf2 哈希 + token）、`app/auth.py`（注册/登录路由）
- `app/beans.py`：纯函数结算（输入：底分、角色、炸弹数、春天 → 输出各账号豆变动），好单测
- `scripts/seed_ai.py`：建账号表、插入 AI 账号、回补豆子
- 阶段 5 起的 SocketIO 房间：`User` 绑定座位，`game_over` 后调用 `beans.py` 结算入库 + 广播

验收标准：
- [ ] 注册/登录/鉴权可用；密码只存哈希；重复用户名被拒
- [ ] `beans.py` 单测：无炸弹/1 炸/2 炸/王炸/春天各场景豆子结余正确（含 DB 落库验证）
- [ ] `seed_ai.py` 生成 N 个 AI 账号且各自有豆；重复运行幂等
- [ ] 豆子 < 房门票 时拒绝入房

我的测试：
```
pytest backend/tests/test_auth.py -v          # 注册/登录/token
pytest backend/tests/test_beans.py -v         # 结算公式
python backend/scripts/seed_ai.py --ensure     # 建表 + 建 AI 账号（幂等）
```

---

## 阶段 3：LLM 决策层（消耗额度的核心）
**工作量：小~中**

### LLM 状态上下文设计（给 LLM"开卷考"）
> 定位：让 LLM 读**一份可读的结构化局面快照**来决策，区别于 DouZero 的 one-hot 闭卷推理。
> 服务端仍是唯一权威：这套上下文只喂给 LLM 参考，出牌结果依旧走 `Game.can_play` 二次校验。

每一轮决策时由 `prompt_builder.py` 构建如下快照（stateless，每次全量重建，无对话历史）：

```
【身份】你是 <名字>，身份 <地主|农民>（农民需写明队友是谁、目标：任一农民先出完）
【我的手牌】<按点数排序，如 4,5,5,7,9,10,J,Q,K,A,2,小王>   （<N>张）
【剩余张数】地主 N 张 | 农民甲 N 张 | 你 N 张
【当前】该你出牌，需压过：<上家>[<牌>]     ← 空表示你领出
【出牌记录】（开局至今，紧凑格式，每行一条 "回合n  名字:[牌] | 名字:过"）
【记牌表】（由规则层算好）  3:剩4  5:已出尽  2:剩2  ... 王:剩1
【规则】牌型：单/对/三/三带一/三带二/顺子(≥5)/连对(≥3对)/飞机/炸弹/王炸；必须压过上家同类型且点数更大；可不出
【输出】只输出JSON：{"action":"play","cards":[...]} 或 {"action":"pass"}
```

要点：
- **身份感知**：地主 1v2；农民需知队友是谁、剩几张、出过什么，才能"配合/让路"
- **保留完整出牌记录**（不是 DouZero 那种最近 15 步），供 LLM 记牌反推
- **记牌表由引擎算好喂给 LLM**，减少它的算术错误（引擎仍每次校验最终出牌）
- **底牌**：正式规则农民不可见，仅地主可见（底牌就在地主手里）
- 可选开关 `LLM_HINT_CANDIDATES`（默认开）：附上规则层算出的合法可压牌型列表，进一步降低非法输出；关闭则更"野"更适合拟人/失误玩法
- 模型参数固定：`response_format=json_object`、`reasoning_effort="none"`（省 65 倍 token，见已提交的 `llm_api_test.py` 验证）

做：
- `key_picker.py`：7 个 key 轮换、失败暂跳过、日志留痕
- `prompt_builder.py`：按上面模板构建快照（从 `game.py` 状态提取）
- `ai_llm.py`：
  1. `prompt_builder` 组装上下文
  2. 调 SenseNova，强制 `json_object` 输出 `{"action":"play|pass","cards":[...]}`
  3. 复用引擎二次校验；非法→重试 1 次→再失败回退规则 AI
- `scripts/hand_test.py`：手工摆局面真实调用 1 次，打印完整 prompt + 决策 + 校验结果

验收标准：
- [ ] `prompt_builder` 单测：身份/手牌/剩牌/记牌表/完整历史都正确渲染，含领出与压牌两种场景
- [ ] mock 模拟 LLM 返回非法牌 → 触发回退，不崩溃
- [ ] key 轮换顺序正确（日志可见）
- [ ] 真实调用 1 次返回合法 JSON 决策（固定 `reasoning_effort="none"`）

我的测试：
```
pytest backend/tests/test_ai_llm.py -v     # mock，不耗额度
python backend/scripts/hand_test.py        # 真实调用 1 次
```

---

## 阶段 4：集成 DouZero 强 AI（「职业选手」档）
**工作量：小（改配置，不写模型）**

做：
- `pip install douzero`，下载官方预训练权重到 `backend/models/`（不入 git，脚本负责拉取）
- `ai_douzero.py` 封装：`pip` 后 import，CPU 推理；接入同一套 AI 接口（实现 `choose_action(state)`）
- 座位配置支持「难度选择」，三档定位见上文「AI 难度设计」：
  - `basic`（规则 AI · 新手）/ `douzero`（职业选手 · 零额度）/ `llm`（拟人玩家 · 允许失误）
- 难度档与对局体验写入配置化 Seat，支持一桌自由混搭（如 真人 + douzero + llm）

验收标准：
- [ ] DouZero 能走通一局且出牌合法
- [ ] `--mix` 支持任意 AI 组合：`llm,llm,llm` / `llm,llm,douzero` / `llm,douzero,douzero` / `douzero,douzero,douzero` / 任意含 `basic`，全部能稳定打完一局
- [ ] LLM 档失败自动回退，不影响整桌游戏

我的测试：
```
python backend/scripts/douzero_smoke.py     # 用预训练模型打一局
python backend/scripts/auto_battle.py 20 --mix llm,llm,llm            # 3 LLM
python backend/scripts/auto_battle.py 20 --mix llm,llm,douzero        # 2 LLM + 1 RL
python backend/scripts/auto_battle.py 20 --mix llm,douzero,douzero    # 1 LLM + 2 RL
python backend/scripts/auto_battle.py 100 --mix basic,douzero,llm     # 混搭无异常（llm 可置空=mock）
```

---

## 阶段 4.5：AI 评论系统（嘲讽 / 夸奖 / 弹幕人格）
**工作量：小~中（纯后端 + 事件流，前端显示随阶段 6 一起做）**

做：
- 按上文「AI 评论系统设计」实现 `doudizhu/commentary/`：
  - `detector.py`：实现检测器清单（踩队友/帮倒忙/不送牌/误伤/送葬/神炸/送跑/绝地）
  - `salience.py`：显著度 = 强度 × 羞耻累计，达标才触发；冷却/每轮上限/每局上限（N/M/K 可配）
  - `phrase_bank.py`：按 archetype 分档短语库（零额度）
  - `llm_commentator.py`：每桌一个的评论 LLM——判断是否值得说、指定 `speaker`、生成措辞（json_object），失败回退短语库，`commentator.mode` 三种模式（rules_only/hybrid/llm_judge）
  - `commentator.py`：订阅 `game` 事件流 → 预筛 → 频控 →（LLM 判断选 modes）→ 广播
- `game.py` 增加事件钩子（play/pass/bomb/round_end/game_end），评论只在天然停顿处输出
- **评论与出牌解耦**：speaker 可为任意 AI 座位（LLM / DouZero / 规则 AI），同一桌混排生效
- 座位人格配置：`off / kind / savage / chatterbox`
- 评价对象包含真人玩家（真人队友坑了 AI，AI 会当面损）

验收标准：
- [ ] 构造"踩队友/送葬/不送牌/神炸"等具体局面，单测断言对应 archetype 触发（确定性，不靠随机）
- [ ] mock 评论事件流 100 盘，全局条数不超过上限（不刷屏）
- [ ] Commentator 指定 `speaker` 为任意 AI 类型座位（含 douzero/规则 AI）均能生效；非 LLM 座位也会被分配台词
- [ ] 三种 mode（rules_only/hybrid/llm_judge）切换正常；LLM 失败时回退短语库，牌局不中断
- [ ] `comment` 事件经 SocketIO 广播格式正确

我的测试：
```
pytest backend/tests/test_commentary.py -v
python backend/scripts/comment_sim.py 100 --mix llm,douzero,basic     # mocker 走事件流，看 douzero/basic 座位也被分台词
python backend/scripts/comment_sim.py 100 --mode llm_judge --mix llm,llm,llm   # 3 LLM + 每回合快速判断（验证抖动/额度）
```

---

## 阶段 5：SocketIO 联机房间
**工作量：中（协议 + 并发）**

做：
- `rooms.py`：6 位房号、创建/加入/退出、座位抢占（真人入座自动顶替 AI）
- SocketIO 事件：`join/create/deal/bid/play/pass/state/reconnect/leave/chat/comment`（`chat`=真人聊天，`comment`=AI 评论）
- 广播策略：整房状态按需全量下发 + 增量事件
- 空位 AI 自动补位（难度默认 `basic`，各座位可独立配置 `basic`/`douzero`/`llm`）
- 断线保留座位 30s，重连后全量同步（SocketIO 自带 reconnect 事件做触发）
- `scripts/ws_clients.py`：3 个模拟客户端加入同一房间完整打完一局

验收标准：
- [ ] 3 个 SocketIO 客户端同一房间完整打完一局
- [ ] 1 真人 + 2 AI 场景广播正确；断线重连续传正常
- [ ] 多房间隔离

我的测试：
```
pytest backend/tests/test_ws_game.py -v
python backend/scripts/ws_clients.py 123456
```

---

## 阶段 6：前端 Vue3 + Vite
**工作量：中（界面 + SocketIO 对接）**

做：
- 房间页：创建/输入房号、座位显示（真人/AI 标签、难度、人格）
- 游戏页：手牌渲染（CSS/SVG 画牌）、出牌区、上下家剩牌、回合提示、叫地主、倒计时、出牌动画
- AI 评论展示：聊天气泡 + 弹幕样式（`comment` 事件），真人聊天区（`chat`），两者样式区分
- `socket.io-client` 对接后端，状态全部服务端广播驱动
- 单机模式 = 1 真人 + 2 AI 本机房间

验收标准：
- [ ] `npm run dev` 启动无报错
- [ ] 一个浏览器窗口可对 2 AI 完整打一局
- [ ] 同局域网两台机器 + 房间号可联机对战

我的测试：
```
cd frontend && npm install && npm run dev
# 后端启动后，浏览器手测；局域网第二台机器访问 http://<局域网IP>:8000 联机
```

---

## 阶段 7：体验完善（可选，按需挑）
**工作量：每一项都小**

做：
- 动画细化、音效、「思考中」AI 提示、结算动画
- 战绩记录（本地 JSON/SQLite）、残局挑战（用多余额度批量生成题库）
- 一键脚本 `run.bat` / `run.sh`：一条命令起后端 + 前端，直接局域网可玩

验收标准：
- [ ] 每项功能有独立验收清单
- [ ] `run.bat` 一条命令起服务，浏览器直接可玩

我的测试：
```
run.bat   # 启动后按提示访问局域网 IP:8000 手测
```

---

## 全局测试清单（每阶段全绿再往下）

| 阶段 | 命令 | 期望 |
|------|------|------|
| 0 | `curl /health` + socketio 握手 | 200 + 握手成功 |
| 1 | `pytest test_game.py` + simulate | 全过 + 整局完成 |
| 2 | `pytest test_ai_basic.py` + auto_battle | 全过 + 100 盘无异常 |
| 2.5 | `pytest test_auth.py` + test_beans.py + seed_ai | 全过 + 建库建 AI 账号幂等 |
| 3 | `pytest test_ai_llm.py` + hand_test | 全过 + 真实调用合法 |
| 4 | `douzero_smoke.py` | 高手 AI 合法打一局 |
| 4.5 | `pytest test_commentary.py` + comment_sim | 全过 + 触发确凿、不刷屏 |
| 5 | `pytest test_ws_game.py` + ws_clients | 全过 + 3 客户端整局 |
| 6 | `npm run dev` + 局域网手测 | 可完整对战 |
| 7 | `run.bat` + 手测 | 一条命令可玩 |

## 进度记录

- [ ] 阶段 0：脚手架与健康检查
- [ ] 阶段 1：复用牌型引擎 + 游戏状态机
- [ ] 阶段 2：规则 AI 兜底
- [ ] 阶段 2.5：账号系统 + 欢乐豆（SQLite）
- [ ] 阶段 3：LLM 决策层
- [ ] 阶段 4：DouZero 强 AI
- [ ] 阶段 4.5：AI 评论系统
- [ ] 阶段 5：SocketIO 联机房间
- [ ] 阶段 6：前端界面
- [ ] 阶段 7：体验完善与一键启动