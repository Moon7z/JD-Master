# JD Master - 智能简历定向优化工具

一个可运行的全栈项目：用户上传原始简历（DOCX/PDF）并输入 Boss 直聘岗位链接，系统自动抓取岗位信息并生成定向优化简历。

## 1. 项目结构

```bash
JD-Master/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口与 API
│   │   ├── config.py                # 配置管理
│   │   ├── schemas.py               # 数据模型
│   │   └── services/
│   │       ├── resume_parser.py     # DOCX/PDF 简历解析
│   │       ├── job_fetcher.py       # 岗位详情抓取
│   │       ├── optimizer.py         # AI 优化（支持 mock / 豆包）
│   │       └── docx_exporter.py     # 导出 DOCX
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # 主界面逻辑
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 2. 功能实现说明

- **简历解析**：支持 docx / pdf，提取个人信息、工作经历、教育、技能、项目等结构化片段。
- **岗位抓取（默认）**：基于真实浏览器访问页面 + OCR识别文本（更接近人类查看页面）。
- **岗位抓取（兼容）**：支持 `httpx + BeautifulSoup` 传统解析作为回退。
- **AI 优化**：
  - 默认 `mock` 模式（无密钥即可运行，便于本地演示）
  - 可切换 `doubao` 模式（配置 API Key 后调用豆包接口）
- **结果输出**：前端展示优化结果，后端支持导出 docx 文件。
- **JD预览入口**：输入岗位链接后可先调用预览接口查看提取到的岗位结构化信息。
- **模型自由配置**：前端与后端体验页都支持按请求输入 `AI Provider / API Key / Model / Base URL`（不落库）。

## 3. 本地启动

### 3.1 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2 前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

打开 `http://localhost:5173`。

## 3.3 一分钟快速体验（无需安装前端依赖）

如果你当前环境无法执行 `npm install`，可以直接使用后端内置体验页：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

然后访问：`http://localhost:8000/`

你可以在该页面直接：
- 上传 `docx/pdf` 简历
- 粘贴 Boss 岗位链接
- 点击“开始优化”
- 点击“下载 DOCX”


## 4. Docker 启动

```bash
docker compose up --build
```

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000/docs`

## 5. API 说明

### `POST /api/job-preview`

- `multipart/form-data`
  - `job_url`: 岗位链接
- 返回：岗位结构化信息（title/company/salary/location/responsibilities/requirements）

### `POST /api/optimize`

- `multipart/form-data`
  - `resume`: docx/pdf 文件
  - `job_url`: 岗位链接
  - `ai_provider`: 可选，`mock`/`doubao`
  - `ai_api_key`: 可选，本次请求使用
  - `ai_model`: 可选，本次请求使用
  - `ai_base_url`: 可选，本次请求使用
- 返回：
  - `optimized_resume_markdown`
  - `parsed_resume`
  - `job_info`

### `POST /api/export`

- `multipart/form-data`
  - `content`: Markdown 简历文本
- 返回：`docx` 二进制下载流

## 6. 豆包 API 配置

在 `backend/.env` 中配置：

```env
AI_PROVIDER=doubao
DOUBAO_API_KEY=your_api_key
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL=doubao-seed-1-6-250615

# 岗位JD抓取模式：ocr_browser(浏览器+OCR) / http(传统HTTP解析)
JD_FETCH_MODE=ocr_browser
```

> 安全建议：生产环境请将密钥存储在密钥管理服务中，不要硬编码。

## 7. 安全与合规建议

- 上传文件大小限制（示例中限制为 10MB）。
- 校验文件扩展名，避免可执行文件上传。
- 不持久化用户简历内容，避免敏感信息落盘。
- 对目标网站抓取频率进行限制，并遵循目标站点 robots 与服务条款。
- 在 UI 中明确添加免责声明与用户授权提示。

## 8. 后续可扩展项

- 增加拖拽上传组件、登录鉴权、任务队列。
- 更强的简历结构化（NER + 段落分类）。
- 针对 Boss 页面反爬引入 Playwright/Selenium + 重试退避机制。
- 支持多模板简历导出（技术岗/产品岗/运营岗）。


## 9. 常见问题（岗位信息为空）

如果你遇到“职位/公司/薪资/地点是占位词，职位描述为空”，通常是页面反爬或动态渲染导致。当前版本已增加多层兜底解析（DOM + title + JSON-LD + 文本回退）。

建议排查：
- 确认岗位链接在浏览器可正常打开且未过期。
- 降低请求频率，避免触发风控。
- 对强反爬页面可改造 `JobFetcher.fetch` 接入 Playwright/Selenium 获取渲染后 HTML。

