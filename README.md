# 安全测试刷题器

基于《安全测试-学习资料.pdf》制作的交互式刷题网页，支持电脑与手机访问。

在线访问：https://\<你的用户名\>.github.io/\<仓库名\>/

## 功能

- 判断题 / 单选题刷题，点击选项自动判分
- 进度保存在浏览器本地（localStorage），错题自动进入错题集
- 错题回顾模式、重置进度
- 进度导出 / 导入，实现电脑与手机跨设备同步
- 题目错误反馈（跳转 GitHub Issues）
- 响应式布局，手机端友好

## 项目结构

```
├── index.html          页面结构
├── styles.css          样式（响应式）
├── app.js              交互逻辑
├── 安全测试-学习资料.pdf  原题库 PDF（可下载）
└── banks/
    ├── index.json              题库索引
    └── safety-test/
        └── questions.json      题库数据（60 题）
```

## 本地运行

```bash
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

## 部署到 GitHub Pages

1. 在 GitHub 新建仓库（如 `lab-safety-quiz`）
2. 将本目录所有文件推送到仓库 `main` 分支
3. 仓库 Settings → Pages → Source 选择 `Deploy from a branch` → 分支 `main` / 目录 `/ (root)` → Save
4. 等待 1-2 分钟后访问 `https://<用户名>.github.io/<仓库名>/`

## 题库格式说明

题库数据在 `banks/<id>/questions.json`，格式：

```json
{
  "meta": { "source": "题库来源说明", "total": 60 },
  "questions": [
    {
      "id": "q1",
      "type": "judge",
      "stem": "题干内容",
      "options": { "A": "对", "B": "错" },
      "answer": "A"
    }
  ]
}
```

`type` 取值：`single` 单选题 / `multiple` 多选题 / `judge` 判断题 / `blank` 填空题。
