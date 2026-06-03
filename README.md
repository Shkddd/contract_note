# ContractReview — 合同智能审核平台

上传 PDF/Word 合同，基于知识库标准条款库进行智能比对与批注。

## 核心功能

- **📄 文档上传** — 支持 PDF、DOCX 格式，自动提取文本并拆分为条款
- **📚 知识库管理** — 维护标准条款库（分类/标签/风险等级），支持增删改查
- **🤖 智能审核** — 逐条比对合同条款与知识库，LLM 驱动差异分析与风险识别
- **✅ 审核报告** — 可视化风险总览 + 逐条批注详情（匹配/冲突/缺失）

## 项目结构

```
contract-review/
├── backend/
│   ├── app/
│   │   ├── config.py              # 配置管理
│   │   ├── main.py                # FastAPI 入口
│   │   ├── models/schemas.py      # Pydantic 数据模型
│   │   ├── services/
│   │   │   ├── db.py              # SQLite 初始化 + 示例数据
│   │   │   ├── document_parser.py # PDF/DOCX 文本提取与条款拆分
│   │   │   ├── knowledge_base.py  # 知识库 CRUD + LLM 语义搜索
│   │   │   └── annotator.py       # LLM 审核引擎
│   │   └── routers/
│   │       ├── documents.py       # 文档上传/列表 API
│   │       ├── knowledge_base.py  # 知识库 CRUD API
│   │       └── review.py          # 审核 API
│   ├── data/uploads/              # 上传文件存储
│   └── requirements.txt
├── frontend/
│   ├── index.html                 # 主页面
│   ├── css/style.css              # 暗色主题样式
│   └── js/app.js                  # 前端逻辑
├── .env.example
└── .gitignore
```

## 快速启动

```bash
# 1. 配置 LLM API Key
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（支持 DeepSeek / OpenAI / 通义千问等）

# 2. 安装依赖
cd backend && pip install -r requirements.txt

# 3. 启动服务
python -m uvicorn app.main:app --port 8001 --reload

# 4. 打开浏览器
open http://localhost:8001
```

## 使用流程

1. **上传合同** → 拖拽或选择 PDF/DOCX 文件
2. **管理知识库** → 新增/编辑标准条款（已内置 10 条示例）
3. **执行审核** → 选择文档，点击「开始审核」，LLM 逐条比对
4. **查看结果** → 风险总览卡片 + 逐条批注详情，含修改建议

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLite |
| 文档解析 | pypdf (PDF)、python-docx (DOCX) |
| 语义搜索 | LLM API (OpenAI 兼容接口) |
| 前端 | 原生 HTML/CSS/JS，暗色主题 |
| 端口 | 8001（避免与 ChatBI 冲突） |
