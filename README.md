# 朱砂戒 · 修身养性之地

> 守元精 · 立志向 · 修身心

[![Version](https://img.shields.io/badge/version-2.0-b8924a.svg)](https://github.com/jihemanyouzhe-boy/zhusha-jie)
[![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Custom-b8924a.svg)](#十开源协议)

一个以中国传统美学（宣纸、朱砂、墨色）为视觉语言的修身打卡与共修社区网站。
帮助同修者通过打卡、诵读、冥想、日记、共勉等方式持戒精进、不孤行。

![朱砂戒](preview.png)

**当前版本：v2.0（2026-08-19 更新）**

---

## 一、网站名称

**朱砂戒**（Zhu Sha Jie）

副标题：修身养性之地

---

## 二、功能概览

### 1. 账号与个人修行
- 注册 / 登录 / 退出（基于 Token 会话）
- 个人主页：连续打卡、功德值、破戒次数、修行天数等数据看板
- 修行设置：用户名、地区、目标天数、个人誓言
- 数据导出：一键下载个人修行记录 JSON

### 2. 每日打卡体系
- **每日打卡**：十六善行（劝善助人、拒一邪念、孝亲尊长、志愿服务、健身运动、早起早眠、清淡饮食、静坐省过、与人为善、洒扫居室、饮水充足、亥时前眠…）
- **戒色日历**：贡献热力图，可视化坚持轨迹
- **今日功课**：晨诵 / 省思 / 运动 / 善行 / 早眠 五项日课

### 3. 戒色挑战
- 自定义天数（7 / 21 / 30 / 90 / 365 日）挑战
- 进行中 / 圆满 / 放弃 三种状态流转
- 破戒归零机制与连续日矫正

### 4. 修心练己
- **冥想修心**：呼吸引导，记录静坐呼吸数
- **定力试炼**：抗邪念计数
- **经典诵读**：寿康宝鉴、弟子规、太上感应篇、清静经、了凡四训
- **励志锦囊**：随机古风箴言
- **答题闯关**：知识问答，记录最佳成绩

### 5. 积德记录
- **功德簿**：累计善行功德
- **戒色日记**：心情 + 文字，支持新增与删除（时间精确到分钟）
- **破戒复盘**：诱因 / 感受 / 教训 三段式反思
- **健康追踪**：睡眠、情绪、运动、备注（按日记录）

### 6. 戒友共修
- **共勉墙**：发布共勉语、互相点赞
- **树洞倾诉**：匿名倾诉、地区标注、暖心点赞
- **专注番茄**：番茄钟专注计时，累计番茄数

### 7. 进阶
- **等级修行**：根据修行数据晋升等级
- **成就殿堂**：解锁各类成就徽章
- **红黑榜**：社区排行

### 8. 其他特性
- **主题切换**：宣纸（日间）/ 墨夜（夜间）双主题，按钮带主题持久态外环
- **联系作者**：弹窗式作者联系信息，一键复制，按钮放大并朱砂高亮
- **响应式设计**：桌面 / 平板 / 手机三端适配
- **完整时间戳**：所有动态内容（树洞、共勉、日记、复盘）日期精确到分钟
- **顶部实时时钟**：每 30 秒自动刷新日期时间，切回标签页立即更新
- **键盘可达性**：所有交互元素支持 `:focus-visible` 朱砂高亮聚焦
- **CSS 变量系统**：宣纸/墨夜双套完整色板（含 `--ink-3` / `--muted` 次级文字色）
- **字体美学**：单字重书法字体用颜色/底色替代 `font-weight:bold`，避免合成加粗模糊

---

## 三、作者联系信息

| 渠道     | 内容               |
| -------- | ------------------ |
| 微信号   | `jihemanyouzhe`    |
| QQ 号    | `1312513825`       |
| 官方 QQ 群 | 朱砂戒（点击网站内"加入官方群聊"按钮入群） |

> 有建议或遇到问题，欢迎联系作者反馈。同修共进，不孤行。

---

## 四、技术栈

| 层     | 技术                                                     |
| ------ | -------------------------------------------------------- |
| 后端   | 纯 Python 3 标准库（`http.server` + `sqlite3` + `threading`） |
| 数据库 | SQLite（单文件持久化，零依赖）                            |
| 前端   | 原生 HTML + CSS + JavaScript（无构建、无框架）            |
| 字体   | Google Fonts：Ma Shan Zheng / Noto Serif SC / ZCOOL XiaoWei |
| 部署   | 任意可运行 Python 3 的服务器                              |

---

## 五、项目结构

```
zhusha-jie/
├── server.py        # 后端：REST API + SQLite + 静态文件服务（监听 8000）
├── index.html       # 前端：单页应用（含全部样式与脚本）
├── favicon.jpg      # 网站图标（朱砂印章风格）
├── README.md        # 项目说明文档
└── data/            # 运行时生成
    └── zhuosha.db   # SQLite 数据库（首次启动自动创建）
```

---

## 六、本地部署

### 环境要求
- Python 3.7+
- 现代浏览器

### 步骤

1. **克隆仓库**

```bash
git clone https://github.com/jihemanyouzhe-boy/zhusha-jie.git
cd zhusha-jie
```

2. **启动后端**（同时提供前端静态文件）

```bash
python3 server.py
```

3. **访问网站**

打开浏览器访问：[http://localhost:8000](http://localhost:8000)

> 首次启动会自动创建 `data/zhuosha.db` 数据库并初始化表结构。

---

## 七、服务器部署（生产环境）

### 1. 后台运行

```bash
nohup python3 server.py > server.log 2>&1 &
```

### 2. 使用 systemd（推荐）

创建 `/etc/systemd/system/zhusha-jie.service`：

```ini
[Unit]
Description=ZhuShaJie Server
After=network.target

[Service]
Type=simple
User=www
WorkingDirectory=/opt/zhusha-jie
ExecStart=/usr/bin/python3 /opt/zhusha-jie/server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable zhusha-jie
sudo systemctl start zhusha-jie
```

### 3. Nginx 反向代理（可选，用于绑定域名 / HTTPS）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 4. 端口说明

- 默认监听 `8000` 端口（双栈 IPv4 + IPv6）
- 修改端口：编辑 [server.py](server.py) 末尾 `DualStackServer(("::", 8000), Handler)`

---

## 八、API 概览

后端路由前缀：`/api`

| 分类     | 接口                                                                   |
| -------- | ---------------------------------------------------------------------- |
| 认证     | `POST /auth/register` `POST /auth/login` `POST /auth/logout` `GET /me` |
| 打卡     | `POST /checkin` `POST /relapse` `POST /daily`                          |
| 挑战     | `POST /challenge/start` `POST /challenge/finish` `POST /challenge/abandon` |
| 修行     | `POST /merit` `POST /classic` `POST /meditation` `POST /pomodoro` `POST /quiz` `POST /resist` |
| 日记     | `GET /journal` `POST /journal` `POST /journal/delete`                  |
| 健康     | `GET /health` `POST /health`                                           |
| 社区     | `GET /treehole` `POST /treehole` `POST /treehole/heart`                |
|          | `GET /encourage` `POST /encourage` `POST /encourage/heart`             |
| 复盘     | `GET /reflections` `POST /reflections` `POST /reflections/delete`      |

> 所有写接口均通过 `X-Token` 请求头进行身份认证（登录后获得）。

---

## 九、数据安全

### 密码与会话
- 用户密码：PBKDF2-HMAC-SHA256 加盐哈希（10 万次迭代）
- 密码比较：`hmac.compare_digest` 常量时间比较，规避理论侧信道
- 会话过期：登录令牌有效期 30 天，过期自动失效；启动时清理过期会话
- 密码长度：限制 4~1024 字符，防止超长口令 CPU DoS

### 静态文件与路径安全
- `/data` 目录访问被禁（403），支持规范化路径防绕过（`/../`、`//`、`./` 等）
- 静态文件后缀白名单：仅放行 `.html/.css/.js/.jpg/.png/.svg/.woff2` 等，阻止 `.db` 等敏感文件

### 请求与跨域
- 请求体上限 1MB（`MAX_BODY_BYTES`），防止内存 DoS
- CORS 跨域预检（OPTIONS）支持，允许从 `file://` 或独立域名调用 API
- 安全响应头：`X-Content-Type-Options: nosniff` / `X-Frame-Options: DENY` / `Referrer-Policy: no-referrer`

### 防刷分
- 答题分数钳制到 `[0, MAX_QUIZ_SCORE]`，且仅奖励超越历史最佳的部分
- 冥想呼吸数钳制到 `[0, MAX_BREATHS=500]`，避免前端伪造巨量数据

### 数据库性能
- WAL 模式：`PRAGMA journal_mode=WAL`，改善读多写少并发
- 关键索引：journal/health/checkins/likes/sessions 全部建索引

### 备份
- 定期备份：建议使用 `cron` 定时备份 `data/` 目录

```bash
# 每日凌晨 3 点备份数据库
0 3 * * * cp /opt/zhusha-jie/data/zhuosha.db /backup/zhuosha_$(date +\%Y\%m\%d).db
```

---

## 十、变更日志

### v2.0（2026-08-19 · 功能与体验升级）

**功能一 · 时辰问候栏**
- 顶部实时时钟依时辰（子丑寅卯…）呈现古典问候语，如「晨光初照 · 神清气爽」，随 30 秒刷新自动切换，配朱砂印章时辰字。

**功能二 · 每日一签**
- 每日依日期稳定抽取吉签（上上 / 上吉 / 中吉…），附签文与持戒小提示，暗合「省察自心」之旨。

**功能三 · 进度圆环**
- 将戒期进度由直线条改为 SVG 朱砂渐变圆环，动效平滑，直观呈现守戒进度百分比。

**功能四 · 心绪便签**
- 每日可记录清静 / 安定 / 沉闷之心绪及随笔，本地持久化，历史以彩色方块形成七日心绪一览。

**功能五 · 名言横幅轮播**
- 首页顶部红色渐变横幅轮播三十六则先贤箴言，印章、圆点导航与左右箭头，自动切换与手点皆可。

**功能六 · 树洞「最新 / 最热」排序**
- 同修心声支持按时间最新或热度最热排序，交互圆润的胶囊切换。

**功能七 · 共勉「最新 / 最暖」排序**
- 共勉墙同样支持最新 / 点赞最暖排序，与树洞保持一致的交互体验。

**功能八 · 打卡庆祝动画**
- 打卡成功弹出一枚「今日已守」朱砂印章庆祝浮层，仪式感十足。

**功能九 · 励志锦囊增强**
- 锦囊支持随机再取与一键抄录到剪贴板，先贤语录全览更顺滑。

**功能十 · 整体 UI 精修**
- 统一圆角、阴影与渐变更协调；修复 `MOODS` 重复声明致命脚本错误（原会导致页面白屏）；补强响应式小屏布局、卡片悬浮、聚焦态等细节。

### v1.0（2026-08-18 · 首发）

**新增功能**
- 完整修身打卡与共修社区网站（30+ API 接口、16 项善行打卡、戒色挑战、冥想、日记、共勉墙、树洞等）
- 宣纸 / 墨夜双主题切换，主题按钮持久态外环视觉反馈
- 顶部实时时钟（30 秒刷新 + 页面可见时刷新），精确到分钟
- 联系作者弹窗（微信 / QQ / QQ 群，一键复制）
- 朱砂印章风格网站 favicon
- 完整时间戳：所有动态内容日期精确到分钟

**安全加固**
- 会话过期机制（30 天）+ 启动时清理
- `/data` 路径规范化屏蔽（4 种绕过全堵）
- 静态文件后缀白名单（防 .db 等敏感文件外泄）
- 密码常量时间比较（`hmac.compare_digest`）
- 请求体 1MB 上限
- CORS 预检 + 安全响应头
- 答题/冥想分数钳制，防止刷分
- 数据库 WAL + 6 个关键索引

**UI 美化**
- 补全 `--ink-3` / `--muted` 次级文字色变量（修复 14+ 处文字层次）
- night 主题品牌色（朱砂、玉绿、金、铜）提亮
- 小字号统一提升（11/10.5px → 12+px），改善中文可读性
- 全局键盘 `:focus-visible` 聚焦样式（无障碍）
- 单字重书法字体去除 `font-weight:bold`，避免合成加粗模糊
- 联系作者按钮与主题按钮类分离，悬停动效更合理
- 联系作者弹窗统一使用 `.show` 类切换，附带淡入动画
- 主题按钮激活态：宣纸主题金色外环 / 夜间主题朱砂外环

---

## 十一、开源协议

本项目由作者 `jihemanyouzhe` 维护，仅供同修学习交流使用。

如需二次开发或商用，请先联系作者获取授权。

---

> 同修共进，不孤行。
