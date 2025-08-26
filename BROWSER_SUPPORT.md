# 浏览器支持说明

## 概述

`htmlextract` 和 `listlink` 工具现在支持使用无头浏览器来获取动态渲染的HTML内容，这对于Vue.js、React、Angular等单页应用(SPA)是必需的。

## 问题背景

Vue.js等现代前端框架开发的网站通常使用JavaScript动态渲染内容。传统的HTTP请求只能获取到初始的HTML模板，无法获取到JavaScript执行后的完整DOM结构。这导致：

- 无法提取到动态生成的内容
- 链接列表为空或不完整
- 页面标题、描述等信息缺失

## 解决方案

### 新增参数

两个工具都新增了 `use_browser` 参数：

- **类型**: boolean
- **默认值**: false
- **说明**: 启用无头浏览器模式来渲染JavaScript内容

### 使用方法

#### htmlextract 工具

```yaml
# 普通模式（适用于静态网站）
url: "https://example.com"
use_browser: false

# 浏览器模式（适用于Vue/React/Angular等SPA）
url: "https://vue-app.com"
use_browser: true
```

#### listlink 工具

```yaml
# 普通模式
url: "https://example.com"
boxclass: "article-list"
use_browser: false

# 浏览器模式
url: "https://vue-app.com"
boxclass: "article-list"
use_browser: true
```

## 技术实现

### 依赖库

- **selenium**: 浏览器自动化库
- **webdriver-manager**: 自动管理ChromeDriver

### 工作流程

1. **检测模式**: 根据 `use_browser` 参数选择获取方式
2. **启动浏览器**: 使用无头Chrome浏览器
3. **页面加载**: 访问目标URL并等待页面完全加载
4. **JavaScript执行**: 等待3秒让JavaScript完成渲染
5. **获取内容**: 提取渲染后的完整HTML
6. **清理资源**: 关闭浏览器释放资源

### 浏览器配置

- 无头模式运行（不显示界面）
- 禁用GPU加速（提高兼容性）
- 设置标准窗口大小（1920x1080）
- 使用真实浏览器User-Agent
- 30秒页面加载超时
- 10秒元素等待超时

## 性能考虑

### 速度对比

- **普通模式**: ~1-2秒
- **浏览器模式**: ~5-10秒

### 资源消耗

- **内存**: 浏览器模式需要额外50-100MB内存
- **CPU**: JavaScript执行需要更多CPU资源

### 使用建议

1. **优先使用普通模式**: 对于静态网站或服务端渲染的网站
2. **必要时使用浏览器模式**: 仅当普通模式无法获取到内容时
3. **批量处理**: 避免同时启动多个浏览器实例

## 错误处理

### 常见错误

1. **依赖缺失**: 提示安装selenium库
2. **Chrome未安装**: webdriver-manager会自动下载ChromeDriver
3. **页面加载超时**: 检查网络连接和目标网站状态
4. **JavaScript错误**: 某些网站可能有兼容性问题

### 故障排除

1. **确保Chrome浏览器已安装**
2. **检查网络连接**
3. **尝试增加等待时间**
4. **查看错误日志**

## 适用场景

### 需要使用浏览器模式的网站类型

- Vue.js应用
- React应用
- Angular应用
- 其他JavaScript重度依赖的SPA
- 内容通过AJAX动态加载的网站

### 可以使用普通模式的网站类型

- 传统服务端渲染网站
- 静态HTML网站
- WordPress等CMS网站
- 大部分新闻网站

## 示例对比

### Vue.js网站示例

```html
<!-- 普通模式获取到的HTML -->
<div id="app">{{ message }}</div>

<!-- 浏览器模式获取到的HTML -->
<div id="app">
  <h1>Welcome to Vue.js!</h1>
  <ul class="article-list">
    <li><a href="/article/1">文章标题1</a></li>
    <li><a href="/article/2">文章标题2</a></li>
  </ul>
</div>
```

通过对比可以看出，浏览器模式能够获取到JavaScript渲染后的完整内容。