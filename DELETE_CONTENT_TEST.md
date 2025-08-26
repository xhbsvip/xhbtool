# 删除内容功能测试说明

## 问题描述

之前的 `deletecontent` 功能在处理英文内容时存在问题，会将包含空格的英文短语错误地分割成多个单词进行删除。

## 修复内容

### 原有问题

```python
# 输入: "hello world"
# 旧逻辑会分割成: ["hello", "world"]
# 结果: 分别删除 "hello" 和 "world"，而不是删除完整短语 "hello world"
```

### 修复后逻辑

```python
# 输入: "hello world"
# 新逻辑保持完整: ["hello world"]
# 结果: 删除完整短语 "hello world"
```

## 使用规则

### 1. 单个删除目标

```yaml
# 删除单个英文单词
deletecontent: "advertisement"

# 删除英文短语
deletecontent: "click here"

# 删除中文内容
deletecontent: "广告"

# 删除中文短语
deletecontent: "点击这里"
```

### 2. 多个删除目标（使用逗号分隔）

```yaml
# 删除多个英文单词
deletecontent: "advertisement, sponsored, promoted"

# 删除多个英文短语
deletecontent: "click here, read more, learn more"

# 删除多个中文内容
deletecontent: "广告, 赞助, 推广"

# 混合删除
deletecontent: "advertisement, 广告, click here, 点击这里"
```

### 3. 包含空格的处理

```yaml
# 正确：删除完整短语
deletecontent: "Terms of Service"

# 正确：删除多个短语
deletecontent: "Terms of Service, Privacy Policy, Cookie Policy"

# 错误：如果想删除多个单独的词，必须用逗号分隔
# 不要这样做: "Terms Service Policy" (会被当作一个完整短语)
# 应该这样做: "Terms, Service, Policy"
```

## 测试用例

### 测试1：英文单词删除

**输入文本**: "This is an advertisement for our product."
**删除内容**: "advertisement"
**预期结果**: "This is an  for our product."

### 测试2：英文短语删除

**输入文本**: "Please click here to continue reading the article."
**删除内容**: "click here"
**预期结果**: "Please  to continue reading the article."

### 测试3：多个英文内容删除

**输入文本**: "This advertisement is sponsored content. Click here for more."
**删除内容**: "advertisement, sponsored, click here"
**预期结果**: "This  is  content.  for more."

### 测试4：中文内容删除

**输入文本**: "这是一个广告内容，请点击这里查看更多。"
**删除内容**: "广告, 点击这里"
**预期结果**: "这是一个内容，请查看更多。"

### 测试5：混合语言删除

**输入文本**: "This is 广告 content. Please click here to see more 内容."
**删除内容**: "广告, click here, 内容"
**预期结果**: "This is  content. Please  to see more ."

## 注意事项

1. **区分大小写**: 删除功能区分大小写，"Advertisement" 和 "advertisement" 是不同的
2. **精确匹配**: 只删除完全匹配的内容，"ad" 不会匹配 "advertisement"
3. **逗号分隔**: 多个删除目标必须用逗号分隔，不能只用空格
4. **空格处理**: 逗号前后的空格会被自动去除
5. **支持所有语言**: 支持中文、英文、日文、韩文等所有Unicode字符

## 最佳实践

1. **单个短语**: 直接输入，不需要引号
2. **多个目标**: 用逗号分隔，每个目标前后的空格会被自动处理
3. **复杂内容**: 对于包含特殊字符的内容，确保输入准确
4. **测试验证**: 建议先用简单内容测试，确认删除效果后再处理复杂内容