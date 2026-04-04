# Study Lab - 项目介绍文档

---

## 一、项目概述

**Study Lab** 是一款基于 Python + PyQt6 + PyQt6-Fluent-Widgets 开发的本地刷题软件，采用简约设计风格，左侧导航栏 + 右侧功能界面的布局。

### 技术栈
- **语言**: Python 3.10+
- **UI 框架**: PyQt6 + PyQt6-Fluent-Widgets（必须使用，不允许使用其他 UI 组件库）
- **数据存储**: 本地 JSON 文件
- **项目结构**: 模块化开发，Python 文件分细

---

## 二、项目目录结构

```
Study_Lab/
├── main.py                     # 程序入口
├── requirements.txt            # 依赖列表
├── config/
│   ├── __init__.py
│   ├── settings.py             # 全局配置（路径、常量等）
│   └── theme.py                # 主题配置
├── core/
│   ├── __init__.py
│   ├── data_manager.py         # 数据管理核心（用户数据、索引操作）
│   ├── user_data.py            # 用户数据模型与操作
│   ├── question_index.py       # 题库索引管理
│   ├── wrong_manager.py        # 错题管理
│   └── favorite_manager.py     # 收藏管理
├── models/
│   ├── __init__.py
│   ├── user.py                 # 用户数据模型
│   ├── question_bank.py        # 题库数据模型
│   ├── wrong_question.py       # 错题数据模型
│   └── favorite_question.py    # 收藏题目数据模型
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # 主窗口（左侧导航 + 右侧内容）
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── home_page.py        # 主页
│   │   ├── local_bank_page.py  # 本地题库界面
│   │   ├── network_bank_page.py# 网络题库界面
│   │   ├── exam_page.py        # 考试界面
│   │   ├── wrong_book_page.py  # 错题本界面
│   │   ├── favorite_page.py    # 收藏夹界面
│   │   ├── settings_page.py    # 设置界面
│   │   └── about_page.py       # 关于界面
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── question_card.py    # 题目卡片组件
│   │   ├── answer_card.py      # 答题卡组件
│   │   ├── index_refresh_dialog.py # 索引刷新对话框
│   │   └── question_detail_dialog.py # 题目详情对话框
│   └── styles/
│       └── qss_loader.py       # 样式加载（如有需要）
├── answer/
│   ├── __init__.py
│   ├── answer_window.py        # 答题窗口基类
│   └── choice_answer.py        # 选择题答题窗口
├── question_bank/              # 题库存储目录
│   ├── index.json              # 题库索引文件
│   ├── chinese/                # 语文题库
│   ├── math/                   # 数学题库
│   ├── english/                # 英语题库
│   ├── computer_basic/         # 计算机基础题库
│   ├── python/                 # Python题库
│   └── mysql/                  # MySQL题库
├── wrong/                      # 错题存储目录
│   ├── index.json              # 错题索引文件
│   ├── chinese.json            # 语文错题
│   ├── math.json               # 数学错题
│   ├── english.json            # 英语错题
│   ├── computer_basic.json     # 计算机基础错题
│   ├── python.json             # Python错题
│   └── mysql.json              # MySQL错题
├── favorite/                   # 收藏存储目录
│   ├── index.json              # 收藏索引文件
│   ├── chinese.json            # 语文收藏
│   ├── math.json               # 数学收藏
│   ├── english.json            # 英语收藏
│   ├── computer_basic.json     # 计算机基础收藏
│   ├── python.json             # Python收藏
│   └── mysql.json              # MySQL收藏
└── data/                       # 用户数据存储目录
    └── user.json               # 用户基础数据
```

---

## 三、数据结构定义

### 3.1 用户数据 (`data/user.json`)

```json
{
  "nickname": "",
  "total_questions": 0,
  "total_study_days": 0,
  "continuous_days": 0,
  "max_continuous_days": 0,
  "last_study_date": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| nickname | string | 用户名（初始版本预留字段） |
| total_questions | int | 累计刷题总数（含重复刷题） |
| total_study_days | int | 累计有学习行为的天数 |
| continuous_days | int | 当前连续打卡天数（每天至少练一套） |
| max_continuous_days | int | 历史最长连续打卡天数 |
| last_study_date | string/null | 上次学习日期（ISO格式，用于计算打卡） |

### 3.2 题库索引 (`question_bank/index.json`)

```json
{
  "chinese": [
    {
      "name": "语文基础选择题库",
      "subject": "chinese",
      "create_time": "2026-04-04T10:00:00"
    }
  ],
  "math": [],
  "english": [],
  "computer_basic": [],
  "python": [],
  "mysql": []
}
```

### 3.3 单个题库文件 (`question_bank/{subject}/{题库名字}.json`)

```json
{
  "name": "语文基础选择题库",
  "subject": "chinese",
  "create_time": "2026-04-04T10:00:00",
  "difficulty": 2,
  "total_questions": 50,
  "questions": [
    {
      "id": 1,
      "question": "题目内容",
      "options": {
        "A": "选项A",
        "B": "选项B",
        "C": "选项C",
        "D": "选项D"
      },
      "answer": "A",
      "explanation": "题目解析"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 题号 |
| question | string | 题目内容 |
| options | object | 选项（ABCD四个键） |
| answer | string | 正确答案（A/B/C/D） |
| explanation | string | 解析 |

### 3.4 错题索引 (`wrong/index.json`)

```json
{
  "chinese": [
    {
      "question_id": "chinese_题库名_1",
      "subject": "chinese",
      "question_content": "题目内容摘要",
      "error_count": 3
    }
  ],
  "math": [],
  "english": [],
  "computer_basic": [],
  "python": [],
  "mysql": []
}
```

### 3.5 单科错题文件 (`wrong/{subject}.json`)

```json
[
  {
    "question_id": "chinese_题库名_1",
    "question_num": 1,
    "bank_name": "语文基础选择题库",
    "bank_question_id": 1,
    "subject": "chinese",
    "question": "题目内容",
    "options": {
      "A": "选项A",
      "B": "选项B",
      "C": "选项C",
      "D": "选项D"
    },
    "answer": "A",
    "explanation": "题目解析",
    "error_count": 3
  }
]
```

### 3.6 收藏索引 (`favorite/index.json`)

```json
{
  "chinese": [
    {
      "question_id": "chinese_题库名_1",
      "subject": "chinese",
      "question_content": "题目内容摘要"
    }
  ],
  "math": [],
  "english": [],
  "computer_basic": [],
  "python": [],
  "mysql": []
}
```

### 3.7 单科收藏文件 (`favorite/{subject}.json`)

```json
[
  {
    "question_id": "chinese_题库名_1",
    "bank_name": "语文基础选择题库",
    "bank_question_id": 1,
    "subject": "chinese",
    "question": "题目内容",
    "options": {
      "A": "选项A",
      "B": "选项B",
      "C": "选项C",
      "D": "选项D"
    },
    "answer": "A",
    "explanation": "题目解析"
  }
]
```

---

## 四、科目与目录映射

| 科目 | 目录名 | 显示名 | 支持题型 |
|------|--------|--------|----------|
| 语文 | chinese | 语文 | 选择题 |
| 数学 | math | 数学 | 选择题 |
| 英语 | english | 英语 | 选择题 |
| 计算机基础 | computer_basic | 机基 | 选择题 |
| Python | python | Python | 后续扩展 |
| MySQL | mysql | MySQL | 后续扩展 |

---

## 五、界面设计

### 5.1 整体布局
- **风格**: 简约设计
- **布局**: 左侧导航栏 + 右侧功能界面
- **组件**: 全部使用 PyQt6-Fluent-Widgets 组件（基于 PyQt6）

### 5.2 主页 (`home_page.py`)
- 居中偏上显示问候语（根据时间变化）：
  - 早上：`"早上好，今天的学习计划是什么？"`
  - 下午：`"下午好，保持节奏，今天的你离目标又近了一步。"`
  - 晚上：`"晚上好，早点休息吧，明天再继续努力。"`
- 下方从左到右显示透明长方形按钮：
  - `开始刷题` -> 跳转到本地题库界面
  - `错题本` -> 跳转到错题本界面
  - `收藏夹` -> 跳转到收藏夹界面

### 5.3 本地题库界面 (`local_bank_page.py`)
- **顶部卡片**：
  - 搜索框（带清空按钮）
  - 下一行：科目筛选下拉框 + 刷新索引按钮
    - 刷新索引流程：
      1. 弹出确认提示：`"该操作会重新检查题库文件夹，题库数量的多少会影响等待时间的长短"`
      2. 点击确定后显示：`"正在检查题库..."` + 圆形不确定进度条
      3. 自动检测题库文件夹，未在索引中的加入，索引中存在但文件不存在的删除
      4. 完成后显示：`"刷新成功"` + 圆形对勾图案
- **下方卡片**：查询结果列表
  - 每项左侧：科目 + 题库名称
  - 每项右侧：创建时间 + 删除按钮
  - 双击弹出确认框，确认后进入对应做题页
  - 分页：每页 50 个题库
- **删除操作**：自动更新对应科目的索引条目（仅更新该题库，不全部检查）

### 5.4 网络题库界面 (`network_bank_page.py`)
- 与本地题库界面结构相同
- **额外功能**：顶部卡片搜索框上方增加链接地址输入框 + 连接按钮
- 连接成功后展示该地址下的所有题库
- 列表项最右侧增加下载按钮
- 下载流程：
  1. 右上角提示：`"正在尝试下载xxx题库，请稍后"`
  2. 开启异步线程下载题库到 `question_bank/{subject}/` 目录
  3. 下载完成提示：`"下载完成"`
  4. 下载失败提示对应错误码

### 5.5 考试界面 (`exam_page.py`)
- 两个子页面（顶部导航栏组件）：
  - `本地考试`：显示"正在开发中"
  - `局域网考试`：显示"正在开发中"

### 5.6 错题本界面 (`wrong_book_page.py`)
- 类似本地题库界面结构
- 顶部卡片：搜索框 + 科目筛选 + 刷新按钮
- 下方列表改为题目列表
- 每项最左侧显示多选框
- 双击题目显示详细信息对话框
- 通过索引定位到对应学科 JSON 文件查询题目详情

### 5.7 收藏夹界面 (`favorite_page.py`)
- 类似错题本界面结构
- 管理 `favorite/` 目录下的收藏题目
- 每项最左侧显示多选框
- 双击题目显示详细信息对话框

### 5.8 设置界面 (`settings_page.py`)
- 使用 PyQt-Fluent-Widgets 官方设置模板样式
- 可设置：
  - 应用主题（Light / Dark / Auto）
  - 主题色
  - 应用语言

### 5.9 关于界面 (`about_page.py`)
- 居中显示：
  - 主标题：`"Study Lab"`
  - 副标题：`"MoZhi"`
  - 小字：`"Beta 开发版本"`

---

## 六、答题界面及其逻辑

### 6.1 选择题答题窗口 (`choice_answer.py`)

**界面布局**：
- **顶部卡片**：
  - 最左侧：返回按钮
  - 中间：当前题库名称
  - 最右侧：重置答题按钮（重置答题区，重新开始）
- **下方左侧**：答题卡组件
  - 显示题号网格
  - 下方显示：已答题数 / 未答题数
- **下方中间**：答题区
  - 上方：题目内容 + 选项（ABCD）
  - 最下方：上一题、下一题、收藏题目按钮

**答题逻辑**：
1. 进入时创建选择题窗口，读取对应题库 JSON 渲染
2. 原 App 窗口最小化到任务栏
3. 用户选择选项后立即对比正确答案
4. 在下方显示正确答案及解析
5. **答对**：等待 1 秒自动跳转下一题
6. **答错**：不自动跳转，将题目写入错题本

### 6.2 题目 ID 生成规则

```
{subject}_{bank_name}_{question_num}
```

例如：`chinese_语文基础选择题库_1`

---

## 七、错误码定义

在可能发生错误的地方设置错误码，闪退时弹出窗口显示对应错误码。

### 错误码规范

| 错误码 | 模块 | 说明 |
|--------|------|------|
| E001 | 数据加载 | 用户数据文件加载失败 |
| E002 | 数据加载 | 用户数据文件格式错误 |
| E003 | 题库索引 | 题库索引文件加载失败 |
| E004 | 题库索引 | 题库索引文件格式错误 |
| E005 | 题库索引 | 题库索引刷新失败 |
| E006 | 题库操作 | 题库文件读取失败 |
| E007 | 题库操作 | 题库文件格式错误 |
| E008 | 题库操作 | 题库文件删除失败 |
| E009 | 题库操作 | 题库文件写入失败 |
| E010 | 错题管理 | 错题文件加载失败 |
| E011 | 错题管理 | 错题文件格式错误 |
| E012 | 错题管理 | 错题写入失败 |
| E013 | 收藏管理 | 收藏文件加载失败 |
| E014 | 收藏管理 | 收藏文件格式错误 |
| E015 | 收藏管理 | 收藏写入失败 |
| E016 | 收藏管理 | 取消收藏失败 |
| E017 | 网络题库 | 网络连接失败 |
| E018 | 网络题库 | 题库下载失败 |
| E019 | 网络题库 | 题库下载链接无效 |
| E020 | 答题界面 | 答题窗口创建失败 |
| E021 | 答题界面 | 题库数据加载失败 |
| E022 | 答题界面 | 答题状态保存失败 |
| E023 | 界面导航 | 页面跳转失败 |
| E024 | 界面导航 | 目标题库不存在 |
| E025 | 系统 | 未知错误 |

### 错误处理实现方式

```python
# 在全局异常钩子中捕获未处理异常
import sys
from PyQt6.QtWidgets import QMessageBox

def exception_handler(exc_type, exc_value, exc_tb):
    # 生成错误报告
    error_msg = f"错误码: {error_code}\n详情: {str(exc_value)}"
    QMessageBox.critical(None, "程序错误", error_msg)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = exception_handler
```

---

## 八、开发规范

### 8.1 UI 组件
- **必须使用** PyQt6 + PyQt6-Fluent-Widgets 组件库
- 不允许使用其他 UI 组件库（如 PySide6、PyQt5 等），以免背景和配置不匹配
- 所有导入语句应使用 `qfluentwidgets` 包（PyQt6 版本）

### 8.2 模块化
- 项目文件夹分类合理
- Python 文件分细，每个功能模块独立文件
- 使用 `__init__.py` 组织包结构

### 8.3 索引自动更新
- 在本地题库界面删除题库等操作时，自动更新索引
- **仅更新该题库对应的索引条目**，不进行全部检查操作

### 8.4 异步操作
- 网络下载使用异步线程（`QThread` 或 `QRunnable`）
- 索引刷新使用异步操作避免阻塞 UI

### 8.5 打卡逻辑
- 每次用户进行答题行为时记录日期
- `continuous_days`：与上次学习日期比较，相差 1 天则 +1，超过 1 天则重置为 1
- `max_continuous_days`：取 `max(max_continuous_days, continuous_days)`
- `total_study_days`：每次有新的学习日期时 +1

---

## 九、依赖

```txt
PyQt6
PyQt6-Fluent-Widgets
requests
```

---

## 十、开发优先级

### Phase 1（核心功能）
1. 项目骨架搭建（目录结构、配置文件）
2. 用户数据管理
3. 题库索引管理
4. 主窗口 + 导航框架
5. 主页
6. 本地题库界面
7. 选择题答题界面

### Phase 2（辅助功能）
1. 错题本界面
2. 收藏夹界面
3. 设置界面
4. 关于界面

### Phase 3（扩展功能）
1. 网络题库界面
2. 考试界面（预留）
3. 打卡统计优化

---

## 十一、注意事项

1. 题库 JSON 文件名使用题库名字（如 `语文基础选择题库.json`）
2. 所有路径使用 `pathlib.Path` 处理，确保跨平台兼容
3. 文件读写操作需加异常处理，返回对应错误码
4. 答题窗口打开时主窗口最小化，关闭后恢复
5. 索引文件在程序启动时加载，修改后及时保存
6. 题目详情对话框使用 PyQt6-Fluent-Widgets 的 `Dialog` 或 `MessageBox` 组件
7. 所有 qfluentwidgets 导入使用 PyQt6 版本的包，例如：`from qfluentwidgets import PushButton`
