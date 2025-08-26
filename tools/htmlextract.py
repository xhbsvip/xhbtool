from collections.abc import Generator
from typing import Any
import requests
from bs4 import BeautifulSoup
import re
import time

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class HtmlExtractTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # 获取参数
        news_url = tool_parameters.get("news-url", "")
        news_title_class = tool_parameters.get("news-title", "")
        news_content_class = tool_parameters.get("news-content", "")
        news_tag_class = tool_parameters.get("news-tag", "")
        news_source_class = tool_parameters.get("news-source", "")
        content_target = tool_parameters.get("content-target", "")
        content_text = tool_parameters.get("content-text", "")
        deletecontent = tool_parameters.get("deletecontent", "")
        use_browser = tool_parameters.get('use_browser', False)
        
        if not news_url:
            yield self.create_text_message("请提供有效的新闻网址")
            return
            
        if not news_title_class or not news_content_class:
            yield self.create_text_message("请提供标题和内容的CSS类名")
            return
        
        try:
            # 根据参数选择获取HTML内容的方式
            if use_browser:
                if not SELENIUM_AVAILABLE:
                    yield self.create_text_message("错误：使用浏览器模式需要安装selenium库，请运行: pip install selenium")
                    return
                html_content = self._get_html_content_with_browser(news_url)
            else:
                html_content = self._get_html_content(news_url)
            
            if not html_content:
                yield self.create_text_message("无法获取网页内容")
                return
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            title = self._extract_content_by_class(soup, news_title_class)
            
            # 提取内容
            content = self._extract_content_by_class(soup, news_content_class)
            
            # 提取标签（可选）
            tags = ""
            if news_tag_class:
                tags = self._extract_content_by_class(soup, news_tag_class)
            
            # 提取来源（可选）
            source = ""
            if news_source_class:
                source = self._extract_content_by_class(soup, news_source_class)
            
            # 提取meta标签中的keywords和description
            keywords = self._extract_meta_content(soup, "keywords")
            description = self._extract_meta_content(soup, "description")
            
            # 执行内容替换（如果有替换参数）
            if content_target and content_text:
                title = self._replace_content(title, content_target, content_text)
                content = self._replace_content(content, content_target, content_text)
                keywords = self._replace_content(keywords, content_target, content_text)
                description = self._replace_content(description, content_target, content_text)
            
            # 执行内容删除（如果有删除参数）
            if deletecontent:
                title = self._delete_content(title, deletecontent)
                content = self._delete_content(content, deletecontent)
                tags = self._delete_content(tags, deletecontent)
                source = self._delete_content(source, deletecontent)
                keywords = self._delete_content(keywords, deletecontent)
                description = self._delete_content(description, deletecontent)
            
            # 输出提取的内容
            yield self.create_variable_message("title", title)
            yield self.create_variable_message("content", content)
            yield self.create_variable_message("tags", tags)
            yield self.create_variable_message("source", source)
            yield self.create_variable_message("keywords", keywords)
            yield self.create_variable_message("description", description)
            yield self.create_variable_message("url", news_url)
            
        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"获取网页内容时出错: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"处理HTML内容时出错: {str(e)}")
    
    def _get_html_content(self, url):
        """获取HTML内容"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 尝试多种编码方式解码HTML内容
        content = response.content
        encodings = ['utf-8', 'gb2312', 'gbk', 'latin1']
        
        for encoding in encodings:
            try:
                html_content = content.decode(encoding)
                return html_content
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用默认的response.text
        return response.text
    
    def _get_html_content_with_browser(self, url):
        """使用无头浏览器获取动态渲染的HTML内容"""
        if not SELENIUM_AVAILABLE:
            return None
        
        driver = None
        try:
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # 创建WebDriver实例（自动下载和管理ChromeDriver）
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # 访问页面
            driver.get(url)
            
            # 等待页面加载完成（等待body元素出现）
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 额外等待JavaScript执行
            time.sleep(3)
            
            # 获取渲染后的HTML
            html_content = driver.page_source
            return html_content
            
        except Exception as e:
            print(f"浏览器获取内容失败: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _extract_content_by_class(self, soup, class_names):
        """根据CSS类名提取内容"""
        if not class_names:
            return ""
        
        # 处理多个类名（用空格或逗号分隔）
        class_list = self._parse_class_names(class_names)
        
        # 尝试不同的选择器策略
        element = None
        
        # 策略1：精确匹配所有类名
        if len(class_list) > 1:
            selector = '.' + '.'.join(class_list)
            element = soup.select_one(selector)
        
        # 策略2：单个类名匹配
        if not element:
            for class_name in class_list:
                element = soup.find(class_=class_name)
                if element:
                    break
        
        # 策略3：包含任意一个类名的元素
        if not element:
            for class_name in class_list:
                elements = soup.find_all(class_=re.compile(class_name))
                if elements:
                    element = elements[0]
                    break
        
        if element:
            # 提取纯文本内容，去除HTML标签
            text = element.get_text(strip=True)
            # 清理多余的空白字符
            text = re.sub(r'\s+', ' ', text)
            return text
        
        return ""
    
    def _delete_content(self, text, delete_str):
        """删除文本中的指定内容"""
        if not text or not delete_str:
            return text
        
        # 解析删除字符串
        delete_targets = self._parse_replacement_strings(delete_str)
        
        # 执行删除
        result_text = text
        for target in delete_targets:
            if target:
                result_text = result_text.replace(target, "")
        
        return result_text
    
    def _replace_content(self, text, target_str, replacement_str):
        """替换文本内容，支持多个目标和替换文本"""
        if not text or not target_str or not replacement_str:
            return text
        
        # 解析目标字符串和替换字符串
        targets = self._parse_replacement_strings(target_str)
        replacements = self._parse_replacement_strings(replacement_str)
        
        # 确保目标和替换文本数量匹配
        min_length = min(len(targets), len(replacements))
        
        # 执行替换
        result_text = text
        for i in range(min_length):
            if targets[i] and replacements[i]:
                result_text = result_text.replace(targets[i], replacements[i])
        
        return result_text
    
    def _parse_replacement_strings(self, input_str):
        """解析替换字符串，支持逗号和空格分隔"""
        if not input_str:
            return []
        
        # 先按逗号分割
        if ',' in input_str:
            # 如果包含逗号，按逗号分割
            parts = input_str.split(',')
            result = []
            for part in parts:
                part = part.strip()
                if part:
                    result.append(part)
            return result
        else:
            # 如果不包含逗号，检查是否包含空格
            input_str = input_str.strip()
            if ' ' in input_str:
                # 包含空格但没有逗号，可能是多个单词的短语或多个单独的词
                # 为了支持英文短语，我们需要更智能的处理
                # 如果用户想要分割多个词，应该使用逗号
                # 这里我们将整个字符串作为一个删除目标
                return [input_str]
            else:
                # 单个词，直接返回
                return [input_str] if input_str else []
    
    def _parse_class_names(self, class_names):
        """解析类名字符串，支持空格和逗号分隔"""
        # 先按逗号分割，再按空格分割
        class_list = []
        parts = class_names.replace(',', ' ').split()
        for part in parts:
            if part.strip():
                class_list.append(part.strip())
        return class_list
    
    def _extract_meta_content(self, soup, meta_name):
        """从HTML meta标签中提取指定属性的内容"""
        # 尝试不同的meta标签格式
        meta_selectors = [
            f'meta[name="{meta_name}"]',
            f'meta[property="{meta_name}"]',
            f'meta[name="{meta_name.lower()}"]',
            f'meta[property="{meta_name.lower()}"]'
        ]
        
        # 如果是description，还要尝试og:description
        if meta_name.lower() == "description":
            meta_selectors.extend([
                'meta[property="og:description"]',
                'meta[name="twitter:description"]'
            ])
        
        # 如果是keywords，还要尝试其他可能的属性名
        if meta_name.lower() == "keywords":
            meta_selectors.extend([
                'meta[name="keyword"]',
                'meta[property="article:tag"]'
            ])
        
        for selector in meta_selectors:
            meta_tag = soup.select_one(selector)
            if meta_tag and meta_tag.get('content'):
                content = meta_tag.get('content').strip()
                if content:
                    return content
        
        return ""
