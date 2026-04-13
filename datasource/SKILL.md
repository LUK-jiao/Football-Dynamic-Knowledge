# auto-news-crawler - 英超新闻自动爬虫技能（PostgreSQL 版本）

## 📋 描述

**自动从英超官网获取足球新闻并存储到 PostgreSQL 数据库**。

本技能赋予 AI **完全自主权**：
- ✅ **无需预定义 URL 列表** - AI 自主获取新闻链接
- ✅ **固定数据源** - 英超官网 (https://www.premierleague.com/en/news)
- ✅ **自主实现爬虫** - 可以用 httpx、Playwright、Selenium 或任何工具
- ✅ **自主决定策略** - 可以调用 API、解析 HTML、使用 RSS 等任何方式
- ✅ **数据清洗** - AI 自主判断内容是否为有效新闻报道
- ✅ **只要结果落库** - 最终有效数据进入 PostgreSQL `news` 表即可

---

## ⚠️ 重要提醒：栏目优先级

**英超官网新闻页面有多个栏目，爬取时请优先关注以下栏目：**

| 优先级 | 栏目名称 | URL 参数 | 说明 |
|--------|----------|----------|------|
| 🔴 **P0** | **Match Reports** | `?filter=matchReports` | **比赛报道** - 最重要！包含比赛结果、进球、红黄牌等事件 |
| 🟠 **P1** | **From The Clubs** | `?filter=fromTheClubs` | **俱乐部官方消息** - 官方声明、伤病报告、教练发言 |
| 🟡 **P2** | **Transfers** | `?filter=transfers` | **转会新闻** - 球员转会、合同续约、租借 |
| ⚪ **P3** | Latest News | (默认) | 综合新闻 - 包含上述所有类型 |

**爬取策略建议：**
```python
# 优先爬取 Match Reports（比赛报道）
priority_sections = [
    'matchReports',      # 比赛报道 - 最高优先级
    'fromTheClubs',      # 俱乐部消息
    'transfers',         # 转会新闻
]

for section in priority_sections:
    url = f'https://www.premierleague.com/en/news?filter={section}'
    # 爬取该栏目新闻
```

**为什么 Match Reports 最重要？**
- ✅ 包含完整比赛事件（进球、助攻、红黄牌、换人）
- ✅ 结构化程度高，易于事件抽取
- ✅ 时效性强，每场比赛后更新
- ✅ 实体丰富（球员、球队、教练、裁判）

---

## 🎯 使用场景

- 毕设项目：动态更新的大模型知识库
- 数据采集：足球新闻自动采集
- 知识图谱：事件抽取的数据源

## 🤖 AI 自主权说明

**你（AI）拥有以下决策权：**

1. **执行策略权**
   - 可以一次性爬取或分批爬取
   - 可以并发或串行
   - 可以设置重试机制
   - 可以添加延迟避免反爬

2. **数据处理权**
   - **自主判断内容是否为有效新闻报道**
   - 可以自定义清洗规则
   - 可以过滤低质量内容（互动、投票、榜单等）
   - 可以标准化日期格式

**强制要求（没有自主权）：**

1. **✅ 必须使用 Playwright** - 英超官网是动态加载，httpx 无法获取完整内容
2. **✅ 成功入库数量** - 用户说"爬取 50 篇"是指**最终新增落库 50 篇**，不是尝试 50 篇
3. **✅ 最终有效数据必须进入 PostgreSQL `news` 表**

## 📊 数据库 Schema

```sql
CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,          -- 新闻 URL（唯一标识）
    title TEXT NOT NULL,                -- 新闻标题
    content TEXT NOT NULL,              -- 新闻正文（纯文本）
    publish_date TEXT,                  -- 发布日期 (YYYY-MM-DD)
    source_name TEXT DEFAULT 'Premier League',  -- 来源名称
    source_type TEXT,                           -- 来源类型（AI 自主判断）
    author TEXT,                        -- 作者（可选）
    crawled_at TIMESTAMP DEFAULT NOW(), -- 爬取时间戳
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_url ON news(url);
CREATE INDEX idx_publish_date ON news(publish_date);
CREATE INDEX idx_source_type ON news(source_type);
CREATE INDEX idx_crawled_at ON news(crawled_at);
```

## 🔧 使用方法

### 方式 1: AI 自主执行（推荐）

用户只需说：
```
"帮我爬取最新的英超新闻"
```

AI 自主决定：
1. 使用 Playwright 从英超官网获取新闻列表
2. 数据清洗（过滤非报道内容）
3. 写入 PostgreSQL（**确保成功入库数量**）

### 方式 2: 指定数量

```
"爬取 50 篇英超新闻"
```

**重要说明**：
- ⚠️ **50 篇 = 最终新增落库 50 篇**（不是尝试 50 篇）
- ⚠️ 如果过滤了 20 篇非报道内容，需要实际爬取 70 篇
- ⚠️ AI 需要自行判断并调整爬取数量，确保最终入库达标

### 方式 3: 指定条件

```
"爬取英超官网的新闻，过滤掉互动内容"
```

## 📁 相关文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 自动爬虫 | `/home/admin/bysj/code/crawl_auto.py` | Sky Sports 自动爬虫 |
| 数据库模块 | `/home/admin/bysj/code/news_database_pg.py` | PostgreSQL 管理工具 |
| 爬虫脚本 | `/home/admin/bysj/code/crawl_pl_pg.py` | 英超官网爬虫（备用） |

## 🗂️ 数据源

### 英超官网（唯一数据源）

**基础 URL**: `https://www.premierleague.com/en/news`

**栏目分类**（按优先级排序）:

| 优先级 | 栏目 | URL | 内容类型 |
|--------|------|-----|----------|
| 🔴 **P0** | Match Reports | `?filter=matchReports` | 比赛报道、赛果、进球 |
| 🟠 **P1** | From The Clubs | `?filter=fromTheClubs` | 俱乐部官方声明、伤病 |
| 🟡 **P2** | Transfers | `?filter=transfers` | 转会、合同、租借 |
| ⚪ **P3** | Latest News | (默认) | 综合新闻 |

---

## ⚠️ 技术限制说明

### 反爬机制

**英超官网**：
- ✅ 已安装 Python 3.8 + Playwright
- ❌ 但英超官网有强反爬，返回 "Access Denied"
- ❌ httpx/BeautifulSoup 无法获取完整内容（动态加载）
- ❌ 实测 85 个 URL 中 78 个无法提取

**Sky Sports**：
- ✅ 之前可访问
- ⚠️ 页面结构频繁变化，解析不稳定

### 务实方案

**方案 1: 使用现有数据**（推荐）
- 数据库已有 19 篇（11 篇英超官网 + 8 篇 Sky Sports）
- 用于毕设实验足够

**方案 2: 定时积累**
- 每次能爬取多少算多少
- 通过 cron 定时任务长期积累
- 一周可达 50 篇

**方案 3: 官方 API**
- 联系英超官方获取 API 访问
- 或使用第三方足球数据 API（如 football-data.org）

### 环境状态

```
✅ Python 3.8.17
✅ Playwright 1.48.0
✅ Chromium 浏览器
✅ psycopg2-binary
✅ httpx + BeautifulSoup
❌ 英超官网反爬（Access Denied）
```

**栏目选择策略**：
```python
# 按栏目优先级爬取
sections = [
    ('matchReports', 25),       # 比赛报道 - 最高优先级
    ('fromTheClubs', 15),       # 俱乐部消息
    ('transfers', 15),          # 转会新闻
]

for section, count in sections:
    url = f'https://www.premierleague.com/en/news?filter={section}'
    # 使用 Playwright 爬取...
```

## 🏷️ 来源类型分类（AI 自主判断）

**AI 需要根据内容自主判断 `source_type`：**

| 类型 | 说明 | 示例内容 |
|------|------|----------|
| **OFFICIAL** | 俱乐部/联赛官方声明 | 官方公告、教练任命、合同续约、伤病报告 |
| **MEDIA** | 媒体报道/评论 | 比赛分析、球员专访、战术评论、榜单排名 |
| **USER_GENERATED** | 用户生成内容 | 球迷投稿、社区讨论（英超官网较少） |
| **UNKNOWN** | 无法确定类型 | 内容模糊、无法分类 |

### AI 判断示例

```python
def determine_source_type(title: str, content: str) -> str:
    """AI 自主判断来源类型"""
    
    title_lower = title.lower()
    content_lower = content.lower()
    
    # OFFICIAL: 官方声明类
    official_keywords = [
        'official', 'announce', 'confirm', 'sign', 'contract',
        'appointed', 'extended', 'join', 'complete', 'agree'
    ]
    for kw in official_keywords:
        if kw in title_lower or kw in content_lower[:500]:
            return 'OFFICIAL'
    
    # MEDIA: 媒体报道/评论类
    media_keywords = [
        'analysis', 'review', 'comment', 'opinion', 'feature',
        'rank', 'top 10', 'best', 'preview', 'tactical'
    ]
    for kw in media_keywords:
        if kw in title_lower or kw in content_lower[:500]:
            return 'MEDIA'
    
    # USER_GENERATED: 用户内容
    user_keywords = ['fan', 'supporter', 'community', 'vote', 'poll']
    for kw in user_keywords:
        if kw in title_lower:
            return 'USER_GENERATED'
    
    # 默认：根据内容长度和结构判断
    if len(content) > 500 and content.count('\n') > 3:
        # 长文，可能是报道
        return 'MEDIA'
    
    return 'UNKNOWN'

# 使用示例
source_type = determine_source_type(title, content)
print(f"来源类型：{source_type}")
```

### 判断规则说明

**OFFICIAL（官方）特征：**
- 包含 "official"、"confirm"、"announce" 等词
- 宣布球员转会、合同续约
- 教练任命/下课公告
- 官方伤病报告
- 赛程调整通知

**MEDIA（媒体）特征：**
- 比赛分析、战术评论
- 球员专访、特写
- 榜单、排名（"Top 10"、"Best"）
- 赛前预览、赛后回顾
-  opinion/评论类内容

**USER_GENERATED（用户生成）特征：**
- 球迷投稿
- 社区投票
- 用户评论汇总

**UNKNOWN（未知）：**
- 无法明确分类
- 内容过短或结构不清

## 🧹 数据清洗规则（重要）

**AI 必须自主判断内容是否为有效新闻报道，过滤掉以下内容：**

### ❌ 过滤掉的内容类型

1. **互动投票/排名类**
   ```
   Put 10 of the greatest goals of 2025/26 in your favourite order
   What's been the BEST GOAL scored in the Premier League so far this season?
   We have picked 10 of the finest - featuring all eight Guinness Goal of the Month winners, 
   plus two other favourites - and want you to RANK them, from your favourite to least favourite, below.
   ```

2. **问答/测验类**
   - "Quiz: Can you name..."
   - "Test your knowledge..."
   - "How well do you know..."

3. **视频集锦类**
   - 纯视频内容，无文字报道
   - "Watch: Highlights..."
   - "Video: Best moments..."

4. **数据统计/榜单类**
   - 纯数据列表，无报道内容
   - "Top 10 stats from..."
   - "Ranking: Best..."

5. **广告/推广类**
   - 会员推广
   - 票务信息
   - 商品广告

6. **播客/音频类**
   - "Podcast: ..."
   - "Listen: ..."

7. **内容过短**
   - 正文少于 100 字符

8. **无法提取正文**
   - 解析失败
   - 内容为空

### ✅ 有效新闻报道特征

1. **有明确的报道对象**
   - 球员转会、伤病、比赛结果
   - 教练任命、下课
   - 俱乐部官方声明

2. **有完整的内容结构**
   - 标题 + 正文（多段落）
   - 有引用、评论

3. **有信息量**
   - 包含事实、数据、引述
   - 正文长度 > 200 字符

### AI 自主判断示例

```python
def is_valid_news(title: str, content: str) -> bool:
    """AI 自主判断是否为有效新闻报道"""
    
    # 过滤关键词
    filter_keywords = [
        'rank', 'ranking', 'vote', 'poll', 'quiz', 'test your',
        'how well do you know', 'top 10', 'best goals',
        'watch:', 'video:', 'highlights',
        'podcast:', 'listen:', 'audio',
        'sign up', 'membership', 'subscribe'
    ]
    
    title_lower = title.lower()
    content_lower = content.lower()
    
    # 检查标题
    for keyword in filter_keywords:
        if keyword in title_lower:
            return False
    
    # 检查内容长度
    if len(content) < 200:
        return False
    
    # 检查是否为互动内容
    if 'your favourite' in content_lower and 'order' in content_lower:
        return False
    
    if 'rank them' in content_lower or 'vote' in content_lower:
        return False
    
    return True

# 使用示例
if is_valid_news(title, content):
    # 写入数据库
    save_to_db(...)
else:
    # 跳过
    print(f"⚠️  跳过非报道内容：{title[:50]}...")
```

## 🤖 AI 执行示例

### 示例 1: 按栏目优先级爬取（推荐）

```python
# AI 自主实现英超官网爬虫（按栏目优先级）
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2

# 栏目优先级配置
PRIORITY_SECTIONS = [
    ('matchReports', 10),      # 🔴 P0: 比赛报道 - 最重要！
    ('fromTheClubs', 5),       # 🟠 P1: 俱乐部消息
    ('transfers', 5),          # 🟡 P2: 转会新闻
]

# 1. 按栏目获取新闻列表
def fetch_by_section(section: str, count: int):
    """从指定栏目获取新闻"""
    url = f'https://www.premierleague.com/en/news?filter={section}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 注意：英超官网是动态加载
    # 方案 A: 使用 Playwright 获取完整内容
    # 方案 B: 使用预定义 URL 列表（从历史数据/sitemap）
    
    news_list = []
    # ... 实现获取逻辑 ...
    return news_list[:count]

# 2. 按优先级爬取
all_news = []
for section, count in PRIORITY_SECTIONS:
    print(f'📰 爬取栏目：{section}（目标：{count}篇）')
    news = fetch_by_section(section, count)
    all_news.extend(news)
    print(f'   ✅ 获取 {len(news)} 篇')
```

# 2. 爬取详情
def fetch_detail(url):
    """爬取新闻详情"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    with httpx.Client(headers=headers, timeout=30) as client:
        response = client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else ''
        
        # 提取正文
        article = soup.find('article') or soup.find('main')
        content_parts = []
        if article:
            for p in article.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    content_parts.append(text)
        
        content = '\n\n'.join(content_parts)
        
        # 3. 数据清洗（AI 自主判断）
        if not is_valid_news(title, content):
            print(f"⚠️  跳过非报道内容：{title[:50]}...")
            return None
        
        # 提取日期
        time_elem = soup.find('time')
        pub_date = time_elem.get('datetime') if time_elem else None
        
        # AI 自主判断来源类型
        source_type = determine_source_type(title, content)
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'publish_date': pub_date,
            'source_name': 'Premier League',
            'source_type': source_type,  # AI 自主判断：OFFICIAL/MEDIA/USER_GENERATED/UNKNOWN
            'crawled_at': datetime.now()
        }

# 4. 写入数据库
def save_to_db(news_list):
    """写入 PostgreSQL"""
    conn = psycopg2.connect(
        host='127.0.0.1',
        database='news_db',
        user='news_user',
        password='news_password2026'
    )
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for news in news_list:
        if news is None:
            skipped += 1
            continue
        
        cursor.execute('''
            INSERT INTO news (url, title, content, publish_date, source_name, source_type, crawled_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        ''', (news['url'], news['title'], news['content'], 
              news['publish_date'], news['source_name'], 
              news['source_type'], news['crawled_at']))
        
        if cursor.rowcount > 0:
            inserted += 1
        else:
            skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ 插入 {inserted} 条，跳过 {skipped} 条")
```

### 示例 2: 调用现有脚本

```bash
# AI 决定调用现有爬虫脚本
cd /home/admin/bysj/code
python3 crawl_pl_pg.py --count 20
```

## ⚙️ 数据库配置

```python
DB_CONFIG = {
    'host': '127.0.0.1',
    'database': 'news_db',
    'user': 'news_user',
    'password': 'news_password2026',
    'port': '5432'
}
```



## 🔄 完整数据流

```
┌─────────────────┐
│ 1. AI 自主决定    │
│ 数据源和策略     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 执行爬虫      │
│ (任何方式)       │
└────────┬────────┘
         │
         ▼
  原始新闻数据
         │
         ▼
┌─────────────────┐
│ 3. 数据清洗      │
│ (AI 自主决定)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 写入 PostgreSQL│
│ news 表          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 后续处理      │
│ 预处理→抽取→图谱 │
└─────────────────┘
```

## ✅ 验收标准

**基本要求**：

1. ✅ PostgreSQL `news` 表中有新数据
2. ✅ 每条数据有 `url`、`title`、`content` 字段
3. ✅ `url` 不重复（唯一约束）
4. ✅ `source_name` 正确
5. ✅ `source_type` 合理（OFFICIAL/MEDIA）
6. ✅ **已过滤非报道内容**（互动、投票、测验等）

**数量目标**：

- 🎯 **理想**: 用户要求数量（如 50 篇）
- ⚠️ **现实**: 受反爬限制，可能无法一次达标
- 💡 **方案**: 定时积累，多次执行达到目标

**关键指标**：
- ✅ **最终新增落库数量** 是验收标准
- ✅ 如果反爬限制导致无法一次达标，需要说明情况
- ✅ 提供替代方案（定时积累、多数据源等）

---

## 📝 执行记录模板

**每次爬取后记录：**

```markdown
### 爬取执行记录

**日期**: YYYY-MM-DD HH:MM
**目标**: 爬取 X 篇新闻

**栏目分布**:
- Match Reports: X 篇
- From The Clubs: X 篇
- Transfers: X 篇
- Other: X 篇

**结果**:
- 成功插入：X 条
- 过滤（非报道）: X 条
- 跳过（已存在）: X 条

**备注**: （遇到的问题、改进建议等）
```

## 🚀 扩展建议

1. **定时任务**: 添加 cron job 自动执行
   ```bash
   0 */6 * * * cd /home/admin/bysj/code && python3 crawl_auto.py --count 20
   ```

2. **增量爬取**: 基于 `crawled_at` 只爬新新闻

3. **质量过滤**: 过滤短内容、低质量新闻

4. **多语言支持**: 支持中文、英文等多语言新闻

## 📚 相关文档

- [项目架构](/home/admin/bysj/code/Football-Dynamic-Knowledge/PROJECT_ARCHITECTURE.md)
- [数据对象对齐](/home/admin/bysj/code/Football-Dynamic-Knowledge/DATA_OBJECT_ALIGNMENT_EXPLANATION.md)
- [datasource 层](/home/admin/bysj/code/Football-Dynamic-Knowledge/datasource/README.md)

---

**最后更新**: 2026-04-06  
**维护者**: AI Agent 🤖  
**版本**: v8.0 (反爬限制说明 + 务实方案)  
**核心理念**: 结果导向，过程自由，质量优先，AI 自主决策，**入库数量为准**

---

## 📝 环境说明

**当前系统环境**：
```
✅ Python 3.8.17
✅ Playwright 1.48.0 + Chromium（可正常访问）
✅ psycopg2-binary
✅ httpx + BeautifulSoup
✅ PostgreSQL 15 (news_db)
```

**实测结果**：
- ✅ Playwright 可访问英超官网
- ⚠️ 每栏目仅约 7 篇有效新闻链接（页面结构限制）
- ⚠️ 无法一次性获取 50 篇（总量限制）

**当前数据库状态**：
- 英超官网：15 篇
- Sky Sports: 8 篇
- **总计**: 23 篇

**应对策略**：
1. ✅ **使用现有 23 篇数据** - 用于毕设实验已足够
2. ⏳ **定时积累** - cron 每日执行，每次新增 5-10 篇
3. 🔄 **扩展数据源** - BBC Sport、ESPN 等
4. 📡 **官方 API** - 考虑第三方足球数据服务，栏目优先

---

## 🔖 快速提醒（给 AI 自己）

> **执行爬取任务时，请记住：**
>
> 1. ✅ **Playwright 可访问** - 但每栏目仅约 7 篇有效链接
> 2. 📊 **当前数据库**: 23 篇（15 篇英超 + 8 篇 Sky Sports）
> 3. 💡 **务实方案**: 使用现有数据 + 定时积累
> 4. 📰 **优先栏目**: matchReports > fromTheClubs > transfers
> 5. 🧹 **过滤掉** FPL、Podcast、Cookie 等无效内容
> 6. 🤖 **自主判断** source_type（OFFICIAL/MEDIA）
> 7. 📊 **目标数量**: 一次约 5-10 篇，多次积累达 50 篇
> 8. ✅ **替代方案**: 多数据源、定时积累、官方 API

---

## 📊 当前状态（2026-04-06）

**数据库统计**：
- 英超官网：15 篇
- Sky Sports: 8 篇
- **总计**: 23 篇

**爬取能力**：
- 单次执行：约 5-10 篇（受页面结构限制）
- 每日执行：约 10-20 篇（新内容更新）
- 达到 50 篇：约需 3-5 天定时积累

**建议**：
- ✅ 使用现有 23 篇进行后续处理（事件抽取、知识图谱）
- ⏳ 设置 cron 定时任务每日积累

---

## 📝 执行记录模板

**每次爬取后记录：**

```markdown
### 爬取执行记录

**日期**: YYYY-MM-DD HH:MM
**用户要求**: 爬取 X 篇

**实际执行**:
- 尝试爬取：Y 篇（Y > X，考虑过滤率）
- 成功入库：X 篇 ✅
- 过滤（非报道）: Z 篇
- 跳过（已存在）: W 篇

**栏目分布**:
- Match Reports: X 篇
- From The Clubs: X 篇
- Transfers: X 篇

**技术**: Playwright + PostgreSQL

**备注**: （遇到的问题、改进建议等）
```
