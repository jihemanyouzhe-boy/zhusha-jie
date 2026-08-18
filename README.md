# 朱砂戒 · 修身养性之地

> 守元精 · 立志向 · 修身心

一个以中国传统美学（宣纸、朱砂、墨色）为视觉语言的修身打卡与共修社区网站。
帮助同修者通过打卡、诵读、冥想、日记、共勉等方式持戒精进、不孤行。

![朱砂戒](favicon.jpg)

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
- **主题切换**：宣纸（日间）/ 墨夜（夜间）双主题
- **联系作者**：弹窗式作者联系信息，一键复制
- **响应式设计**：桌面 / 平板 / 手机三端适配
- **完整时间戳**：所有动态内容（树洞、共勉、日记、复盘）日期精确到分钟

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

- 用户密码：PBKDF2-HMAC-SHA256 加盐哈希（10 万次迭代）
- 数据库文件：`data/zhuosha.db`（通过 `/data` 路径访问会被禁止）
- 定期备份：建议使用 `cron` 定时备份 `data/` 目录

```bash
# 每日凌晨 3 点备份数据库
0 3 * * * cp /opt/zhusha-jie/data/zhuosha.db /backup/zhuosha_$(date +\%Y\%m\%d).db
```

---

## 十、开源协议

本项目由作者 `jihemanyouzhe` 维护，仅供同修学习交流使用。

如需二次开发或商用，请先联系作者获取授权。

---

> 同修共进，不孤行。
