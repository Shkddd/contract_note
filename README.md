# ContractReview — 合同智能审核平台

上传 PDF/Word 合同，基于知识库标准条款库进行智能比对，输出带**原生注释气泡**的批注版合同。

## 核心功能

- **📄 文档上传** — 支持 PDF、DOCX 格式，自动提取文本并拆分为条款
- **📚 知识库管理** — 维护标准条款库（分类/标签/风险等级），支持增删改查
- **🤖 智能审核** — 批量比对合同条款与知识库，LLM 驱动差异分析与风险识别
- **✅ 审核报告** — 可视化风险总览 + 逐条批注详情（匹配/冲突/缺失）
- **💬 原生注释导出** — 下载带批注的 PDF/DOCX，批注以原生注释气泡呈现（鼠标悬停/点击查看全文）
- **⚡ 批量分析** — 所有条款一次性发送 LLM，避免逐条串行调用

## 项目结构

```
contract-review/
├── backend/
│   ├── app/
│   │   ├── config.py              # 配置管理（LLM、数据库路径）
│   │   ├── main.py                # FastAPI 入口 + 静态文件挂载
│   │   ├── models/schemas.py      # Pydantic 数据模型
│   │   ├── services/
│   │   │   ├── db.py              # SQLite 初始化 + 示例数据
│   │   │   ├── document_parser.py # PDF/DOCX 文本提取与条款拆分
│   │   │   ├── knowledge_base.py  # 知识库 CRUD + LLM 语义搜索
│   │   │   ├── annotator.py       # LLM 批量审核引擎
│   │   │   └── annotated_export.py# 批注版导出（PDF/DOCX 原生注释）
│   │   └── routers/
│   │       ├── documents.py       # 文档上传/列表/删除 API
│   │       ├── knowledge_base.py  # 知识库 CRUD API
│   │       └── review.py          # 审核 + 批注版下载 API
│   ├── data/uploads/              # 上传文件存储
│   └── requirements.txt
├── frontend/
│   ├── index.html                 # 主页面
│   ├── css/style.css              # 暗色主题样式
│   └── js/app.js                  # 前端逻辑
├── scripts/
│   └── create_test_contracts.py   # 测试合同生成脚本
├── .env.example
└── .gitignore
```

## 快速启动

```bash
# 1. 配置 LLM API Key（支持 DeepSeek / OpenAI / 通义千问等 OpenAI 兼容接口）
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL

# 2. 安装依赖
cd backend && pip install -r requirements.txt

# 3. 启动服务
python -m uvicorn app.main:app --port 8001 --reload

# 4. 打开浏览器
open http://localhost:8001
```
<img width="2856" height="1382" alt="image" src="https://github.com/user-attachments/assets/f0814be3-aaca-4016-9001-4dbb3001e4c8" />

<img width="2934" height="1320" alt="image" src="https://github.com/user-attachments/assets/d3d92063-e76e-4050-989a-8c4957001eab" />
<img width="2938" height="1358" alt="image" src="https://github.com/user-attachments/assets/b1b05140-435d-4f6e-886b-1b54534b4a7d" />
<img width="2448" height="1472" alt="image" src="https://github.com/user-attachments/assets/248940c3-99fd-40c1-80cb-f9619fc7bfcf" />




## 使用流程

1. **上传合同** → 拖拽或选择 PDF/DOCX 文件，自动解析为条款
2. **管理知识库** → 新增/编辑标准条款（已内置 10+ 条示例，含风险等级）
3. **执行审核** → 选择文档，点击「开始审核」，全部条款一次性发送 LLM 分析
4. **查看结果** → 风险总览卡片 + 逐条批注详情（匹配/冲突/缺失），含修改建议
5. **下载批注版** → 点击「下载批注版」，获得带原生注释的 PDF/DOCX 文件

## 批注版导出格式

| 格式 | 批注方式 | 查看方式 |
|------|---------|---------|
| **PDF** | PDF 文本注释（Comment 图标） | 点击/悬停图标弹出批注气泡 |
| **DOCX** | Word 原生注释 | 右侧边栏气泡，条款标题带风险颜色高亮 |

批注内容包含：匹配类型、风险等级、参考标准条款、AI 评语、修改建议。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLite |
| 文档解析 | pypdf (PDF)、python-docx (DOCX) |
| 语义搜索 | LLM API (OpenAI 兼容接口) |
| 批注导出 | fpdf2 (PDF 文本注释)、python-docx + ZIP 注入 (DOCX 原生注释) |
| 前端 | 原生 HTML/CSS/JS，暗色主题 |
| 端口 | 8001 |

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `LLM_API_KEY` | API 密钥 | `sk-xxx` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
